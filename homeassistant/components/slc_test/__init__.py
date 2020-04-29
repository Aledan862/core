"""The Smart Life Comfort integration."""
import asyncio
import logging
import socket
import requests

import sys

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform
# from homeassistant.helpers.entity_registry import (
#     async_get_registry,
#     EntityRegistry
# )

from .const import (
    DOMAIN,
    DEFAULT_PORT,
    EVENT,
    SLC_START,
    SLC_SYNC
)
from homeassistant.const import (
    CONF_HOST,
    # CONF_PASSWORD,
    CONF_PORT,
    CONF_TYPE,
    # CONF_USERNAME,
    # EVENT_COMPONENT_LOADED,
    EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP,
)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)


# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["light", "switch", "sensor"]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Smart Life Comfort component."""
    # Data that you want to share with your platforms
    controllerip = config[DOMAIN][CONF_HOST]
    port = config[DOMAIN][CONF_PORT]
    _LOGGER.info("SLC Host: " + controllerip)

    hostname = socket.gethostname()
    IPAddr = socket.gethostbyname(hostname)
    _LOGGER.info("Your Computer Name is:" + hostname)
    _LOGGER.info("Your Computer IP Address is:" + IPAddr)
    res = False
    try:
        url = "http://" + str(controllerip) + ":" + str(port)
        _LOGGER.debug("url: " + url)
        response_code = requests.get(url).status_code
        _LOGGER.debug("response_code: " + str(response_code))
        if response_code == 200 or response_code == "200":
            hass.data[DOMAIN] = config[DOMAIN]
            _LOGGER.info("SLC platform started!")
            res = True
            hass.bus.async_fire(DOMAIN, {CONF_TYPE: "loaded"})
            # hass.helpers.discovery.load_platform('sensor', DOMAIN, {}, config)
            for platform in PLATFORMS:
                _LOGGER.debug("starting SLC {}...".format(platform))
                hass.async_create_task(async_load_platform(hass, platform, DOMAIN, {}, config))
        else:
            _LOGGER.error("unable to connect to LoxoneRio")
    except:
        e = sys.exc_info()[0]
        _LOGGER.error(e)
        return False

    slc = SLCclient(host="192.168.100.158", controllerip=controllerip)

    async def message_callback(event_type, message):
        if event_type == 2:
            hass.bus.async_fire(SLC_START, message)
        elif event_type == 3:
            hass.bus.async_fire(SLC_SYNC, message)
        elif event_type == 4:
            hass.bus.async_fire(EVENT, message)

    async def connect_handler(event):
        if event.data["State"] == "CONNECTING":
            # registry = await async_get_registry(hass)
            # idList = hass.states.async_entity_ids("switch") + hass.states.async_entity_ids("light")
            # for e in idList:
            #     if registry.async_get(e):
            #         if registry.async_get(e).platform == DOMAIN:
            #             _LOGGER.debug(registry.async_get(e))

            await slc.connect(event.data)

    async def start_slc_rio(event):
        await slc.start()

    async def stop_slc_rio(event):
        _ = await slc.stop()
        _LOGGER.debug(_)

    res = False

    try:
        res = await slc.async_init()
    except ConnectionError:
        _LOGGER.error("Connection Error")

    if res is True:
        slc.message_call_back = message_callback
        hass.bus.async_listen(SLC_START, connect_handler)
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_START, start_slc_rio)
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, stop_slc_rio)
    else:
        res = False
        _LOGGER.info("Error")
    return res


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up Smart Life Comfort from a config entry."""
    # TODO Store an API object for your platforms to access
    # hass.data[DOMAIN][entry.entry_id] = MyApi(...)

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok


class SLCLink:
    SOCKET_TIMEOUT = 2.0
    RX_PORT = 5555
    TX_PORT = 4445
    # the_queue = queue.Queue()
    # thread = None
    link_ip = ""

    def __init__(self, link_ip=None):
        if link_ip is not None:
            SLCLink.link_ip = link_ip

    # methods
    def send_not_reliable_message(self, msg):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        sock.sendto(msg.encode(), (SLCLink.link_ip, SLCLink.TX_PORT))
        _LOGGER.debug("Send data: %s", msg)
        return True


class SLCclient:
    def __init__(self,
                 host="192.168.100.158",
                 port="5555",
                 controllerip="192.168.100.147"):
        self._host = host
        self._rxport = port
        self._txport = 4445
        self._controllerip = controllerip

        self.message_call_back = None
        self._pending = []

        self.connect_retries = 10
        self.connect_delay = 30
        self.state = "CLOSED"
        self.stream = None

    async def async_init(self):
        import asyncio_dgram
        self.stream = await asyncio_dgram.bind((self._host, self._rxport))
        _LOGGER.debug(f"Serving on {self.stream.sockname}")
        self.state = "CONNECTED"
        return True

    async def slc_listen(self, stream):
        try:
            while True:
                data, remote_addr = await self.stream.recv()
                _LOGGER.debug(f"Echoing {data.decode()!r}")
                event_type, parsed_data = await self.parse_slc_data(data.decode())
                _LOGGER.debug(f"event_type {event_type}")
                _LOGGER.debug(f"parsed_data {parsed_data}")
                if self.message_call_back is not None:
                    if parsed_data != {}:
                        await self.message_call_back(event_type, parsed_data)
                await asyncio.sleep(0)
        except:
            pass

    async def parse_slc_data(self, data_string: str):
        event_dict = {}
        keys = ["Channel", "Number", "Value"]
        if data_string.strip().upper() == "CONNECTING":
            event_dict = {"State" : "CONNECTING"}
            event_type = 2
        elif data_string.strip().upper() == "STARTING":
            event_dict = {"State" : "STARTING"}
            event_type = 3
        else:
            data_string = data_string.strip().split(':')
            if len(data_string) > 1:
                event_dict = dict(zip(keys, data_string))
                event_type = 4
        return (event_type, event_dict)

    async def keep_alive(self, future, interval_seconds):
        while not future.done():
            # print("waiting...")
            await asyncio.sleep(interval_seconds)
        print("done!")

    async def start(self):
        server_task = asyncio.create_task(self.slc_listen(self.stream))
        keep_alive_task = asyncio.create_task(self.keep_alive(server_task, 1.0))
        await asyncio.wait([server_task, keep_alive_task])

        # self._pending.append(consumer_task)

        # for task in pending:
        #     task.cancel()

        # if self.state != "STOPPING":
        #     self.state == "CONNECTING"
        #     self._pending = []
        #     for i in range(self.connect_retries):
        #         _LOGGER.debug("reconnect: {} from {}".format(i + 1, self.connect_retries))
        #         await self.stop()
        #         await asyncio.sleep(self.connect_delay)
        #         res = await self.reconnect()
        #         if res is True:
        #             await self.start()
        #             break

    async def reconnect(self):
        return await self.async_init()

    async def connect(self, data):
        self.send_not_reliable_message_to("Connected#")

    async def stop(self):
        try:
            self.state = "STOPPING"
            self.stream.close()
            return 1
        except:
            return -1

        # methods
    def send_not_reliable_message_to(self, msg):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # Internet  # UDP
        sock.sendto(msg.encode(), (self._controllerip, self._txport))
        _LOGGER.info(msg)
        return True
