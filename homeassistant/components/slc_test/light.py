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
from .const import DOMAIN

DEVICE_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required("type"): vol.In(["DMX", "DMXRGB", "DMXRGBW"]),
        vol.Required("channel"): cv.byte,
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
        if device_type == "DMX":
            light = SLCLight(name, device_id, channel, slclink)
        elif device_type == "DMXRGB":
            light = SLCRGB(name, device_id, channel, slclink)
        # elif device_type == "DMXRGBW":
        #     light = SLCRGBW(name, device_id, channel, slclink)
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


class SLCLight(Light):
    """ Provides a SLC light. """

    def __init__(self, name, device_id, channel, slclink):
        """Initialize an SLCLight."""
        self._name = name
        self._device_id = device_id
        self._channel = channel
        self._state = None
        self._brightness = 255
        self._slclink = slclink

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

    @property
    def supported_features(self):
        """Flag supported features."""
        return SUPPORT_BRIGHTNESS

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
    def is_on(self):
        """Return true if light is on."""
        return self._state

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


class SLCRGB(Light):
    """ Provides a SLC RGB light. """

    def __init__(self, name, device_id, channel, slclink):
        """Initialize an SLCLight."""
        self._name = name
        self._device_id = device_id
        self._channel = channel
        self._state = None
        self._slclink = slclink
        self._brightness = 0
        self._hs_color = (0, 0)

    @property
    def name(self):
        """Return the display name of this light."""
        return self._name

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

    async def async_turn_on(self, **kwargs):
        """ Turn the light on. """
        self._state = True
        msg = ""
        rgb_color = (0, 0, 0)
        _LOGGER.info(kwargs)

        h, s = self._hs_color
        brightness = self._brightness

        if ATTR_BRIGHTNESS in kwargs:
            brightness = self._brightness = kwargs[ATTR_BRIGHTNESS]

        elif ATTR_HS_COLOR in kwargs:
            h, s = self._hs_color = (kwargs[ATTR_HS_COLOR][0], kwargs[ATTR_HS_COLOR][1])

        rgb_color = color_RGB_and_brightness_to_RGB(brightness, color_util.color_hs_to_RGB(h, s))

        msg = "DMXRGB:%d:%d,%d,%d#" % (
            self._channel,
            rgb_color[0],
            rgb_color[1],
            rgb_color[2],
        )

        self._slclink.send_not_reliable_message(msg)
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the LightWave light off. """
        self._state = False

        msg = "DMXRGB:%d:0,0,0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)

        self.async_schedule_update_ha_state()


class SLCRGBW(SLCRGB):
    """ Provides a SLC RGBW light. """

    async def async_turn_on(self, **kwargs):
        """ Turn the light on. """
        self._state = True
        msg = ""
        rgb_color = (0, 0, 0)
        rgbw_color = (0, 0, 0, 0)

        _LOGGER.info(kwargs)

        h, s = self._hs_color
        brightness = self._brightness

        if ATTR_BRIGHTNESS in kwargs:
            brightness = self._brightness = kwargs[ATTR_BRIGHTNESS]

        elif ATTR_HS_COLOR in kwargs:
            h, s = self._hs_color = (kwargs[ATTR_HS_COLOR][0], kwargs[ATTR_HS_COLOR][1])

        rgb_color = color_RGB_and_brightness_to_RGB(brightness, color_util.color_hs_to_RGB(h, s))
        rgbw_color = color_util.color_rgb_to_rgbw(rgb_color[0], rgb_color[1], rgb_color[2])

        msg = "DMXRGBW:%d:%d,%d,%d#" % (
            self._channel,
            rgbw_color[0],
            rgbw_color[1],
            rgbw_color[2],
            rgbw_color[3],
        )

        self._slclink.send_not_reliable_message(msg)
        self.async_schedule_update_ha_state()

    async def async_turn_off(self, **kwargs):
        """ Turn the LightWave light off. """
        self._state = False

        msg = "DMXRGBW:%d:0,0,0,0#" % (self._channel)
        self._slclink.send_not_reliable_message(msg)

        self.async_schedule_update_ha_state()
