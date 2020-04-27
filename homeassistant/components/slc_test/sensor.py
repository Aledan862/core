"""Support sensor integration."""
import logging

from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    STATE_ON, STATE_OFF, STATE_UNAVAILABLE)
# Import the device class from the component that you want to support
# from homeassistant.const import CONF_HOST

from .const import (
    EVENT,
    SINGLE,
    DOUBLE,
    TRIPLE,
    LONG)


_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """Set up the sensors"""
    _LOGGER.info("SLC Sensor started!")
    sensors = []

    for channel in range(1, 24):
        name = "DI" + str(channel)
        new_sensor = SLCSensor(name, "DI", channel, hass)
        hass.bus.async_listen(EVENT, new_sensor.event_handler)
        sensors.append(new_sensor)

    for channel in range(1, 8):
        name = "AI" + str(channel)
        new_sensor = SLCSensor(name, "AI", channel, hass)
        hass.bus.async_listen(EVENT, new_sensor.event_handler)
        sensors.append(new_sensor)

    ibutton_sensor = SLCSensor("IButton", "IBTN", 1, hass)
    hass.bus.async_listen(EVENT, ibutton_sensor.event_handler)
    sensors.append(ibutton_sensor)

    async_add_entities(sensors)
    return True


class SLCSensor(Entity):
    """Representation of a Sensor."""

    def __init__(self, name, sensortyp, channel, hass):
        """Initialize the sensor."""
        self._state = STATE_UNAVAILABLE
        self._name = name
        self._channel = channel
        self._hass = hass
        self._sensortyp = sensortyp
        self._format = None
        self._unit_of_measurement = None
        self._on_state = STATE_ON
        self._off_state = STATE_OFF

    async def event_handler(self, event):
        if self._sensortyp == event.data["Channel"]:
            if (self._sensortyp == "AI") and (self._channel == int(event.data["Number"])):
                self._state = round(float(event.data["Value"]), 1)
            elif self._sensortyp == "DI" and (self._channel == int(event.data["Number"])):
                val = int(event.data["Value"])
                # _LOGGER.debug(val)
                if val == 0:
                    self._state = self._off_state
                else:
                    if val == 1:
                        click_type = SINGLE
                    elif val == 2:
                        click_type = DOUBLE
                    elif val == 3:
                        click_type = TRIPLE
                    elif val == 7:
                        self._state = self._on_state
                        click_type = LONG
                    else:
                        _LOGGER.warning("Unsupported click_type detected: %s", val)
                        return
                    self._hass.bus.fire(
                        EVENT + ".click",
                        {"entity_id": self._name, "click_type": click_type},
                    )
            elif self._sensortyp == "IBTN":
                _LOGGER.debug("ibutton")
                if int(event.data["Number"]) == 1:
                    self._hass.bus.fire(
                        EVENT + ".alarm",
                        {"entity_id": self._name, "state": "correct"},
                    )
                elif int(event.data["Number"]) == -1:
                    self._hass.bus.fire(
                        EVENT + ".alarm",
                        {"entity_id": self._name, "state": "wrong"},
                    )

            self.schedule_update_ha_state()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def should_poll(self):
        return False

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._format is not None:
            try:
                return self._format % self._state
            except ValueError:
                return self._state
        else:
            return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return device specific state attributes.

        Implemented by platform classes.
        """
        return {"device_typ": self._sensortyp + "_sensor",
                "channel_number": self._channel,
                "platform": "slc",
                "show_last_changed": "true"}
