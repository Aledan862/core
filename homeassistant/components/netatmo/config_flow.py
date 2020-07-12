"""Config flow for Netatmo."""
import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_SHOW_ON_MAP
from homeassistant.core import callback
from homeassistant.helpers import config_entry_oauth2_flow, config_validation as cv

from .const import (
    CONF_AREA_NAME,
    CONF_LAT_NE,
    CONF_LAT_SW,
    CONF_LON_NE,
    CONF_LON_SW,
    CONF_NEW_AREA,
    CONF_PUBLIC_MODE,
    CONF_WEATHER_AREAS,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NetatmoFlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler, domain=DOMAIN
):
    """Config flow to handle Netatmo OAuth2 authentication."""

    DOMAIN = DOMAIN
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_POLL

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return NetatmoOptionsFlowHandler(config_entry)

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return logging.getLogger(__name__)

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        scopes = [
            "read_camera",
            "read_homecoach",
            "read_presence",
            "read_smokedetector",
            "read_station",
            "read_thermostat",
            "write_camera",
            "write_presence",
            "write_thermostat",
        ]

        if self.flow_impl.name != "Home Assistant Cloud":
            scopes.extend(["access_camera", "access_presence"])
            scopes.sort()

        return {"scope": " ".join(scopes)}

    async def async_step_user(self, user_input=None):
        """Handle a flow start."""
        await self.async_set_unique_id(DOMAIN)
        return await super().async_step_user(user_input)

    async def async_step_homekit(self, homekit_info):
        """Handle HomeKit discovery."""
        return await self.async_step_user()


class NetatmoOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Netatmo options."""

    def __init__(self, config_entry: config_entries.ConfigEntry):
        """Initialize Netatmo options flow."""
        self.config_entry = config_entry
        self.options = dict(config_entry.options)
        self.options.setdefault(CONF_WEATHER_AREAS, {})

    async def async_step_init(self, user_input=None):
        """Manage the Netatmo options."""
        return await self.async_step_public_weather_areas()

    async def async_step_public_weather_areas(self, user_input=None):
        """Manage configuration of Netatmo public weather areas."""
        errors = {}

        if user_input is not None:
            new_client = user_input.pop(CONF_NEW_AREA, None)
            areas = user_input.pop(CONF_WEATHER_AREAS, None)
            user_input[CONF_WEATHER_AREAS] = {
                area: self.options[CONF_WEATHER_AREAS][area] for area in areas
            }
            self.options.update(user_input)
            if new_client:
                return await self.async_step_public_weather(
                    user_input={CONF_NEW_AREA: new_client}
                )

            return await self._update_options()

        weather_areas = list(self.options[CONF_WEATHER_AREAS])

        data_schema = vol.Schema(
            {
                vol.Optional(
                    CONF_WEATHER_AREAS, default=weather_areas,
                ): cv.multi_select(weather_areas),
                vol.Optional(CONF_NEW_AREA): str,
            }
        )
        return self.async_show_form(
            step_id="public_weather_areas", data_schema=data_schema, errors=errors,
        )

    async def async_step_public_weather(self, user_input=None):
        """Manage configuration of Netatmo public weather sensors."""
        if user_input is not None and CONF_NEW_AREA not in user_input:
            self.options[CONF_WEATHER_AREAS][user_input[CONF_AREA_NAME]] = user_input
            return await self.async_step_public_weather_areas()

        orig_options = self.config_entry.options.get(CONF_WEATHER_AREAS, {}).get(
            user_input[CONF_NEW_AREA], {}
        )

        default_longitude = self.hass.config.longitude
        default_latitude = self.hass.config.latitude
        default_size = 0.04

        data_schema = vol.Schema(
            {
                vol.Optional(CONF_AREA_NAME, default=user_input[CONF_NEW_AREA]): str,
                vol.Optional(
                    CONF_LAT_NE,
                    default=orig_options.get(
                        CONF_LAT_NE, default_latitude + default_size
                    ),
                ): cv.latitude,
                vol.Optional(
                    CONF_LON_NE,
                    default=orig_options.get(
                        CONF_LON_NE, default_longitude + default_size
                    ),
                ): cv.longitude,
                vol.Optional(
                    CONF_LAT_SW,
                    default=orig_options.get(
                        CONF_LAT_SW, default_latitude - default_size
                    ),
                ): cv.latitude,
                vol.Optional(
                    CONF_LON_SW,
                    default=orig_options.get(
                        CONF_LON_SW, default_longitude - default_size
                    ),
                ): cv.longitude,
                vol.Required(
                    CONF_PUBLIC_MODE, default=orig_options.get(CONF_PUBLIC_MODE, "avg"),
                ): vol.In(["avg", "max"]),
                vol.Required(
                    CONF_SHOW_ON_MAP, default=orig_options.get(CONF_SHOW_ON_MAP, False),
                ): bool,
            }
        )

        return self.async_show_form(step_id="public_weather", data_schema=data_schema)

    async def _update_options(self):
        """Update config entry options."""
        return self.async_create_entry(
            title="Netatmo Public Weather", data=self.options
        )
