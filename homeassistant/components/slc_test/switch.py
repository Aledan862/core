"""Support switch device"""
import logging

from homeassistant.helpers.entity import ToggleEntity

# Import the device class from the component that you want to support
from homeassistant.const import CONF_HOST

from . import SLCLink
from .const import (
    DOMAIN,
    SLC_SYNC
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Setup switches """
    _LOGGER.info("SLC Switch started!")
    switches = []
    # Assign configuration variables.
    # The configuration check takes care they are present.
    host = hass.data[DOMAIN][CONF_HOST]
    slclink = SLCLink(host)
    # generate a default set of switches
    for channel in range(1, 24):
        name = "DO" + str(channel)
        new_switch = SLCSwitch(name, channel, slclink)
        hass.bus.async_listen(SLC_SYNC, new_switch.event_handler)
        switches.append(new_switch)

    # Add devices
    async_add_entities(switches)
    _LOGGER.info("SLC Switch complete!")


class SLCSwitch(ToggleEntity):
    """Representation of a switch."""
    def __init__(self, name, channel, slclink):
        self._name = name
        self._channel = channel
        self._state = False
        self._slclink = slclink

        msg = "DO:%d:0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return self._name

    @property
    def should_poll(self):
        """ No polling needed for a LightWave light. """
        return False

    async def event_handler(self, event):
        if self._state:
            msg = "DO:%d:1#" % (self._channel)
            self._slclink.send_not_reliable_message(msg)

    async def async_turn_on(self, **kwargs):
        """ Turn the switch on. """
        self._state = True

        msg = "DO:%d:1#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the switch off. """
        self._state = False

        msg = "DO:%d:0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)
        self.async_schedule_update_ha_state()

    async def async_toggle(self, **kwargs):
        """Toggle the entity."""
        if self.is_on:
            await self.async_turn_off(**kwargs)
        else:
            await self.async_turn_on(**kwargs)
