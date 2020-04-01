"""Platform for sensor integration."""
import logging
import voluptuous as vol
# from RPi import GPIO
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorDevice
# from homeassistant.components import rpi_gpio
# from homeassistant.helpers.entity import Entity
from homeassistant.helpers.dispatcher import dispatcher_send, async_dispatcher_connect
import homeassistant.helpers.config_validation as cv
from homeassistant.core import callback
# import asyncio
# import board
# import busio

_LOGGER = logging.getLogger(__name__)

SIGNAL_UPDATE_ENTITY = "my_custom_component_update_{}"

CONF_PIN = "pin"
CONF_ADDRESS = "address"

DEFAULT_ADDRESS = 0x10
DEFAULT_INTERRUPT_PIN = 17

_SENSORS_SCHEMA = vol.Schema({cv.positive_int: cv.string})

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_PIN): _SENSORS_SCHEMA,
        vol.Optional(CONF_ADDRESS, default=DEFAULT_ADDRESS): vol.Coerce(int),
    }
)

UPDATE_MESSAGE_SCHEMA = vol.Schema(
    {vol.Required("number"): cv.positive_int, vol.Required("state"): cv.positive_int}
)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensor platform."""
    pins = config.get(CONF_PIN)
    # address = config.get(CONF_ADDRESS)

    sensor_data = dict()

    def read_initial_input(hass, port):
        # send_buf_initial = [0xee, port]
        # rec_buf_initial = []
        #
        # i2c.writeto_then_readfrom(DEFAULT_ADDRESS, bytes(send_buf_initial),
        #                           bytes(rec_buf_initial))
        #
        # sensor_data[port] = (rec_buf_initial[0] & 0x01)
        #
        # return sensor_data[port]
        return 1

    @callback
    def read_input(service):
        """Read a value from a GPIO."""
        # send_buf = [0xff]
        # rec_buf = []
        #
        # i2c.writeto_then_readfrom(DEFAULT_ADDRESS, bytes(send_buf), bytes(rec_buf))
        #
        pin_number = service.data["number"]
        pin_state = service.data["state"]

        sensor_data[pin_number] = pin_state

        dispatcher_send(hass, SIGNAL_UPDATE_ENTITY.format(pin_number))

    # GPIO.setup(DEFAULT_INTERRUPT_PIN, GPIO.IN, GPIO.PUD_UP)
    # GPIO.add_event_detect(DEFAULT_INTERRUPT_PIN, GPIO.FALLING, callback=read_input,
    #                       bouncetime=50)
    hass.services.async_register(
        "shs_bs", "update", read_input, schema=UPDATE_MESSAGE_SCHEMA
    )

    binary_sensors = []
    for pin_num, pin_name in pins.items():
        sensor_data[pin_num] = read_initial_input(hass, pin_num)
        binary_sensors.append(SHS_bs(pin_name, pin_num, sensor_data))

    async_add_entities(binary_sensors, True)


class SHS_bs(BinarySensorDevice):
    """Representation of a Sensor."""

    def __init__(self, name, pin, sensor_data):
        """Initialize the sensor."""
        self._name = name
        self._pin = pin
        self._sensor_data = sensor_data
        self._state = None
        self._remove_signal_update = None

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    async def async_added_to_hass(self):
        """Call when entity is added to hass."""
        self._remove_signal_update = async_dispatcher_connect(
            self.hass, SIGNAL_UPDATE_ENTITY.format(self._pin), self._update_callback
        )

    async def async_will_remove_from_hass(self) -> None:
        """Call when entity will be removed from hass."""
        self._remove_signal_update()

    @callback
    def _update_callback(self):
        """Call update method."""
        self.async_schedule_update_ha_state(True)

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    async def async_update(self):
        """Fetch new state data for the sensor."""
        if self._pin in self._sensor_data:
            self._state = self._sensor_data[self._pin]
