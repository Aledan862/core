"""Platform for light integration."""
import logging
# import asyncio
# import queue
# import threading
# import socket
# import numpy as np
import voluptuous as vol

import homeassistant.util.color as color_util
import homeassistant.helpers.config_validation as cv

# Import the device class from the component that you want to support
from homeassistant.const import CONF_DEVICES, CONF_NAME, CONF_HOST
from homeassistant.components.light import (
    Light,
    ATTR_BRIGHTNESS,
    ATTR_HS_COLOR,
    SUPPORT_COLOR,
    # SUPPORT_COLOR_TEMP,
    SUPPORT_BRIGHTNESS,
    # SUPPORT_TRANSITION,
    PLATFORM_SCHEMA,
)

from . import SLCLink
from .const import (
    DOMAIN,
    SLC_SYNC,
    EVENT,
)

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required("type"): vol.In(["DMX", "DMXRGB", "DMXRGBW"]),
        vol.Required("channel"): cv.byte,
        vol.Optional("dmxin", default=0): cv.byte,
    }
)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Optional(CONF_HOST): cv.string,
        vol.Optional(CONF_DEVICES, default={}): {cv.string: DEVICE_SCHEMA},
    }
)

_LOGGER = logging.getLogger(__name__)


def color_RGB_and_brightness_to_RGB(brightness: int, rgb=(0, 0, 0)):
    """Combine RGB and brightness"""
    rgb = [int((x / 255.0) * brightness) for x in rgb]
    return tuple(rgb)


def interp(x, in_min, in_max, out_min, out_max):
    """Linear interpolation"""
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    """ Find and return DMX lights """
    _LOGGER.info("SLC Light started!")
    lights = []
    # Assign configuration variables.
    # The configuration check takes care they are present.
    host = hass.data[DOMAIN][CONF_HOST]

    slclink = SLCLink(host)

    for device_id, device_config in config.get(CONF_DEVICES, {}).items():
        name = device_config[CONF_NAME]
        channel = device_config["channel"]
        device_type = device_config["type"]
        dmxin_channel = device_config["dmxin"]
        if device_type == "DMX":
            light = SLCLight(name, device_id, channel, slclink)
        elif device_type == "DMXRGB":
            light = SLCRGB(name, device_id, channel, slclink, dmxin_channel)
            hass.bus.async_listen(EVENT, light.event_handler)
        elif device_type == "DMXRGBW":
            light = SLCRGBW(name, device_id, channel, slclink, dmxin_channel)
            hass.bus.async_listen(EVENT, light.event_handler)
        hass.bus.async_listen(SLC_SYNC, light.sync_event_handler)
        lights.append(light)
    # if len(lights) == 0:
    # # Config is empty so generate a default set of dimmers
    #     for device in range(1, 20):
    #         name = "Dimmer ch" + str(device)
    #         device_id = "DMX" + str(device)
    #         lights.append(SLCLight(name, device_id, device,  slcink))

    # Add devices
    async_add_entities(lights)
    _LOGGER.info("SLC Light complete!")


class SLCLight(LightEntity):
    """ Provides a SLC light. """

    def __init__(self, name, device_id, channel, slclink):
        """Initialize an SLCLight."""
        self._name = name
        self._device_id = device_id
        self._channel = channel
        self._state = None
        self._brightness = 255
        self._slclink = slclink

        self.entity_id = f"light.{self._device_id}"

        msg = "DMX:%d:0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"DMX{self._channel}"

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

    @property
    def should_poll(self):
        """ No polling needed for a light. """
        return False

    @property
    def brightness(self):
        """Return the brightness of the light.

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    async def sync_event_handler(self, event):
        """ Send current saved state in HA to controller when it started. """
        if self._state:
            msg = "DMX:%d:%d#" % (self._channel, self._brightness)
            self._slclink.send_not_reliable_message(msg)

    async def async_turn_on(self, **kwargs):
        """ Turn the light on. """
        self._state = True
        msg = ""

        if ATTR_BRIGHTNESS in kwargs:
            self._brightness = kwargs[ATTR_BRIGHTNESS]
            msg = "DMX:%d:%d#" % (self._channel, self._brightness)
        else:
            msg = "DMX:%d:%d#" % (self._channel, self._brightness)

        self._slclink.send_not_reliable_message(msg)
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the LightWave light off. """
        self._state = False

        msg = "DMX:%d:0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)

        self.async_schedule_update_ha_state()


class SLCRGB(LightEntity):
    """ Provides a SLC RGB light. """

    def __init__(self, name, device_id, channel, slclink, dmxin_channel=0):
        """Initialize an SLCLight."""
        self._name = name
        self._device_id = device_id
        self._channel = channel
        self._state = None
        self._slclink = slclink
        self._brightness = 255
        self._hs_color = (0, 0)
        self._dmxin = dmxin_channel

        self.entity_id = f"light.{self._device_id}"

        msg = "DMXRGB:%d:0,0,0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return a unique ID."""
        return f"DMX{self._channel}"

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS | SUPPORT_COLOR

    @property
    def should_poll(self):
        """ No polling needed for a LightWave light. """
        return False

    @property
    def brightness(self):
        """Return the brightness of the light.

        This method is optional. Removing it indicates to Home Assistant
        that brightness is not supported for this light.
        """
        return self._brightness

    @property
    def hs_color(self):
        return self._hs_color

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    async def sync_event_handler(self, event):
        if self._state:
            msg = "DMX:%d:%d#" % (self._channel, self._brightness)
            self._slclink.send_not_reliable_message(msg)

    async def event_handler(self, event):
        """ Change state provided by new event from DMXIN """
        if (event.data["Channel"] == "DMXIN"):
            if (self._dmxin == int(event.data["Number"])):
                r, g, b, w = event.data["Value"].strip().split(',')
                r = int(r)
                g = int(g)
                b = int(b)
                w = int(w)

        r, g, b = color_util.color_rgbw_to_rgb(r, g, b, w)

        self._slclink.send_not_reliable_message(f"DMXRGB:{self._channel}:{r},{g},{b}#")
        self._hs_color = color_util.color_RGB_to_hs(r, g, b)

        if r == g == b == 0:
            self._state = False
        else:
            self._state = True

        self.async_schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        """ Turn the light on. """
        self._state = True

        h, s = self._hs_color
        brightness = self._brightness

        if ATTR_BRIGHTNESS in kwargs:
            brightness = self._brightness = kwargs[ATTR_BRIGHTNESS]

        elif ATTR_HS_COLOR in kwargs:
            h, s = self._hs_color = (kwargs[ATTR_HS_COLOR][0], kwargs[ATTR_HS_COLOR][1])

        r, g, b = color_RGB_and_brightness_to_RGB(brightness, color_util.color_hs_to_RGB(h, s))

        self._slclink.send_not_reliable_message(f"DMXRGB:{self._channel}:{r},{g},{b}#")
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the LightWave light off. """
        self._state = False

        msg = "DMXRGB:%d:0,0,0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)

        self.async_schedule_update_ha_state()


class SLCRGBW(SLCRGB):
    """ Provides a SLC RGBW light. """

    async def event_handler(self, event):
        """ Change state provided by new event from DMXIN """
        if (event.data["Channel"] == "DMXIN"):
            if (self._dmxin == int(event.data["Number"])):
                r, g, b, w = event.data["Value"].strip().split(',')
                r = int(r)
                g = int(g)
                b = int(b)
                w = int(w)

                self._slclink.send_not_reliable_message(f"DMXRGBW:{self._channel}:{r},{g},{b},{w}#")

                r, g, b = color_util.color_rgbw_to_rgb(r, g, b, w)
                self._hs_color = color_util.color_RGB_to_hs(r, g, b)

                if r == g == b == w == 0:
                    self._state = False
                else:
                    self._state = True

        self.async_schedule_update_ha_state()

    async def async_turn_on(self, **kwargs):
        """ Turn the light on. """
        self._state = True

        h, s = self._hs_color
        brightness = self._brightness

        if ATTR_BRIGHTNESS in kwargs:
            brightness = self._brightness = kwargs[ATTR_BRIGHTNESS]

        elif ATTR_HS_COLOR in kwargs:
            h, s = self._hs_color = (kwargs[ATTR_HS_COLOR][0], kwargs[ATTR_HS_COLOR][1])

        r, g, b = color_RGB_and_brightness_to_RGB(brightness, color_util.color_hs_to_RGB(h, s))
        r, g, b, w = color_util.color_rgb_to_rgbw(r, g, b)

        self._slclink.send_not_reliable_message(f"DMXRGBW:{self._channel}:{r},{g},{b},{w}#")
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the LightWave light off. """
        self._state = False

        msg = "DMXRGBW:%d:0,0,0,0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)

        self.async_schedule_update_ha_state()
