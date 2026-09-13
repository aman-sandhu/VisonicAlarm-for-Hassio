"""Support for Visonic Alarm components."""

from __future__ import annotations

import logging
import threading
from datetime import datetime, timedelta

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.entity import Entity
from homeassistant.util import Throttle
import homeassistant.helpers.config_validation as cv


_LOGGER = logging.getLogger(__name__)


CONF_NO_PIN_REQUIRED = "no_pin_required"
CONF_USER_CODE = "user_code"
CONF_APP_ID = "app_id"
CONF_USER_EMAIL = "user_email"
CONF_USER_PASSWORD = "user_password"
CONF_PANEL_ID = "panel_id"
CONF_PARTITION = "partition"
CONF_EVENT_HOUR_OFFSET = "event_hour_offset"

STATE_ATTR_SYSTEM_NAME = "system_name"
STATE_ATTR_SYSTEM_SERIAL_NUMBER = "serial_number"
STATE_ATTR_SYSTEM_MODEL = "model"
STATE_ATTR_SYSTEM_READY = "ready"
STATE_ATTR_SYSTEM_ACTIVE = "active"
STATE_ATTR_SYSTEM_CONNECTED = "connected"

DEFAULT_NAME = "Visonic Alarm"
DEFAULT_PARTITION = "ALL"

DOMAIN = "visonicalarm"

PLATFORMS = [
    "sensor",
    "alarm_control_panel",
]

# Keep this global for compatibility with older code.
HUB = None


CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required(CONF_HOST): cv.string,
                vol.Required(CONF_APP_ID): cv.string,
                vol.Required(CONF_USER_CODE): cv.string,
                vol.Required(CONF_USER_EMAIL): cv.string,
                vol.Required(CONF_USER_PASSWORD): cv.string,
                vol.Required(CONF_PANEL_ID): cv.string,
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
    },
    extra=vol.ALLOW_EXTRA,
)


class VisonicAlarmHub(Entity):
    """Visonic Alarm hub wrapper class."""

    def __init__(self, domain_config, visonicalarm):
        """Initialize the Visonic Alarm hub."""

        self.config = domain_config
        self._visonicalarm = visonicalarm
        self._last_update = None
        self._lock = threading.Lock()

        self.alarm = visonicalarm.System(
            domain_config[CONF_HOST],
            domain_config[CONF_APP_ID],
            domain_config[CONF_USER_CODE],
            domain_config[CONF_USER_EMAIL],
            domain_config[CONF_USER_PASSWORD],
            domain_config[CONF_PANEL_ID],
            domain_config.get(
                CONF_PARTITION,
                DEFAULT_PARTITION,
            ),
        )

    def connect(self):
        """Set up a connection to the Visonic API server."""

        try:
            self.alarm.connect()
            return True

        except Exception as ex:
            _LOGGER.error(
                "Connection failed: %s",
                ex,
            )
            return False

    @property
    def last_update(self):
        """Return the last update timestamp."""

        return self._last_update

    @Throttle(timedelta(seconds=10))
    def update(self):
        """Update all alarm statuses."""

        try:
            if self.alarm.is_token_valid is False:
                self.alarm.connect()

            self.alarm.update_status()
            self.alarm.update_devices()

            self._last_update = datetime.now()

        except Exception as ex:
            _LOGGER.error(
                "Update failed: %s",
                ex,
            )
            raise

    @property
    def name(self):
        """Return the name of the hub."""

        return "Visonic Alarm Hub"


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    """Handle configuration.yaml and import it into the UI."""

    if DOMAIN in config:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={
                    "source": "import",
                },
                data=config[DOMAIN],
            )
        )

    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Visonic Alarm from a config entry."""

    global HUB

    from .visonic import alarm as visonicalarm

    # Start with the original config-entry data.
    # Then allow anything saved in Configure / Options
    # to override those values.
    config = {
        **entry.data,
        **entry.options,
    }

    hub = VisonicAlarmHub(
        config,
        visonicalarm,
    )

    connected = await hass.async_add_executor_job(
        hub.connect
    )

    if not connected:
        raise ConfigEntryNotReady(
            "Could not connect to Visonic Alarm"
        )

    try:
        await hass.async_add_executor_job(
            hub.update
        )

    except Exception as err:
        raise ConfigEntryNotReady(
            f"Could not retrieve Visonic Alarm status: {err}"
        ) from err

    hass.data.setdefault(
        DOMAIN,
        {},
    )

    hass.data[DOMAIN][entry.entry_id] = hub

    # Temporary compatibility with older platform code.
    HUB = hub

    # Reload the integration automatically whenever
    # its Options / Configure settings are changed.
    entry.async_on_unload(
        entry.add_update_listener(
            async_reload_entry
        )
    )

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    return True


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload Visonic Alarm when options are changed."""

    await hass.config_entries.async_reload(
        entry.entry_id
    )


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload a Visonic Alarm config entry."""

    global HUB

    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hub = hass.data.get(
            DOMAIN,
            {},
        ).pop(
            entry.entry_id,
            None,
        )

        if HUB is hub:
            HUB = None

    return unload_ok
