"""Config flow for Visonic Alarm."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from . import (
    CONF_APP_ID,
    CONF_EVENT_HOUR_OFFSET,
    CONF_NO_PIN_REQUIRED,
    CONF_PANEL_ID,
    CONF_PARTITION,
    CONF_USER_CODE,
    CONF_USER_EMAIL,
    CONF_USER_PASSWORD,
    DEFAULT_NAME,
    DEFAULT_PARTITION,
    DOMAIN,
    VisonicAlarmHub,
)
from .options_flow import VisonicOptionsFlow

_LOGGER = logging.getLogger(__name__)


STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): TextSelector(),
        vol.Required(CONF_APP_ID): TextSelector(),
        vol.Required(CONF_USER_CODE): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
            )
        ),
        vol.Required(CONF_USER_EMAIL): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.EMAIL,
                autocomplete="username",
            )
        ),
        vol.Required(CONF_USER_PASSWORD): TextSelector(
            TextSelectorConfig(
                type=TextSelectorType.PASSWORD,
                autocomplete="current-password",
            )
        ),
        vol.Required(CONF_PANEL_ID): TextSelector(),
        vol.Optional(
            CONF_PARTITION,
            default=DEFAULT_PARTITION,
        ): cv.string,
        vol.Optional(
            CONF_NAME,
            default=DEFAULT_NAME,
        ): cv.string,
        vol.Optional(
            CONF_NO_PIN_REQUIRED,
            default=False,
        ): cv.boolean,
        vol.Optional(
            CONF_EVENT_HOUR_OFFSET,
            default=0,
        ): vol.All(
            vol.Coerce(int),
            vol.Range(min=-24, max=24),
        ),
    }
)


class VisonicConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for Visonic Alarm."""

    VERSION = 1

    @staticmethod
    def async_get_options_flow(config_entry):
        """Return the Visonic Alarm options flow."""
        return VisonicOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Handle setup from the Home Assistant UI."""

        errors: dict[str, str] = {}

        if user_input is not None:
            unique_id = (
                f"{user_input[CONF_HOST]}_"
                f"{user_input[CONF_PANEL_ID]}"
            )

            await self.async_set_unique_id(unique_id)
            self._abort_if_unique_id_configured()

            try:
                from .visonic import alarm as visonicalarm

                hub = VisonicAlarmHub(
                    user_input,
                    visonicalarm,
                )

                connected = await self.hass.async_add_executor_job(
                    hub.connect
                )

                if not connected:
                    errors["base"] = "cannot_connect"

            except Exception as err:
                _LOGGER.exception(
                    "Unexpected error connecting to Visonic Alarm: %s",
                    err,
                )
                errors["base"] = "unknown"

            if not errors:
                return self.async_create_entry(
                    title=user_input.get(
                        CONF_NAME,
                        DEFAULT_NAME,
                    ),
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
        )

    async def async_step_import(
        self,
        import_config: dict[str, Any],
    ):
        """Import existing configuration.yaml settings."""

        unique_id = (
            f"{import_config[CONF_HOST]}_"
            f"{import_config[CONF_PANEL_ID]}"
        )

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=import_config.get(
                CONF_NAME,
                DEFAULT_NAME,
            ),
            data=import_config,
        )
