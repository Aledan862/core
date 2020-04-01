"""The Smart Life Comfort integration."""
import asyncio
import logging
import socket

import homeassistant.helpers.config_validation as cv
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.discovery import async_load_platform

from .const import DOMAIN
from homeassistant.const import (
    CONF_HOST,
    # CONF_PASSWORD,
    # CONF_PORT,
    # CONF_USERNAME,
    # EVENT_COMPONENT_LOADED,
    # EVENT_HOMEASSISTANT_START,
    # EVENT_HOMEASSISTANT_STOP,
)


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                # vol.Optional(CONF_PORT, default=DEFAULT_PORT): cv.port,
            }
        ),
    },
    extra=vol.ALLOW_EXTRA,
)

EVENT = 'slc_event'
# TODO List the platforms that you want to support.
# For your initial PR, limit it to 1 platform.
PLATFORMS = ["light", "switch"]
_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the Smart Life Comfort component."""
    # Data that you want to share with your platforms
    host = config[DOMAIN][CONF_HOST]
    _LOGGER.info("SLC Host: " + host)

    hass.data[DOMAIN] = config[DOMAIN]

    _LOGGER.info("SLC Light started!")
    # hass.helpers.discovery.load_platform('sensor', DOMAIN, {}, config)
    for platform in PLATFORMS:
        _LOGGER.debug("slarting SLC {}...".format(platform))
        hass.async_create_task(async_load_platform(hass, platform, DOMAIN, {}, config))
    return True


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
        _LOGGER.info(msg)
        return True
