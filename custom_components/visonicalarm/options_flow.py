"""Options flow for Visonic Alarm."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME

from . import (
    CONF_EVENT_HOUR_OFFSET,
    CONF_NO_PIN_REQUIRED,
    CONF_PARTITION,
    DEFAULT_NAME,
    DEFAULT_PARTITION,
)


class VisonicOptionsFlow(config_entries.OptionsFlow):
    """Handle Visonic Alarm options."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ):
        """Manage Visonic Alarm options."""

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=user_input,
            )

        current = {
            **self.config_entry.data,
            **self.config_entry.options,
        }

        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_PARTITION,
                    default=current.get(
                        CONF_PARTITION,
                        DEFAULT_PARTITION,
                    ),
                ): str,
                vol.Optional(
                    CONF_NAME,
                    default=current.get(
                        CONF_NAME,
                        DEFAULT_NAME,
                    ),
                ): str,
                vol.Optional(
                    CONF_NO_PIN_REQUIRED,
                    default=current.get(
                        CONF_NO_PIN_REQUIRED,
                        False,
                    ),
                ): bool,
                vol.Optional(
                    CONF_EVENT_HOUR_OFFSET,
                    default=current.get(
                        CONF_EVENT_HOUR_OFFSET,
                        0,
                    ),
                ): vol.All(
                    vol.Coerce(int),
                    vol.Range(min=-24, max=24),
                ),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )
