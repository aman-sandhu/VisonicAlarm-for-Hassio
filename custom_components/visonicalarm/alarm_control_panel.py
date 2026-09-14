"""Interfaces with the Visonic Alarm control panel."""

from __future__ import annotations

import logging
from datetime import timedelta
from time import sleep

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
import homeassistant.components.persistent_notification as pn
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_CODE_FORMAT,
    EVENT_STATE_CHANGED,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant

from . import (
    DOMAIN,
    CONF_EVENT_HOUR_OFFSET,
    CONF_NO_PIN_REQUIRED,
    CONF_USER_CODE,
)

_LOGGER = logging.getLogger(__name__)


SUPPORT_VISONIC = (
    AlarmControlPanelEntityFeature.ARM_HOME
    | AlarmControlPanelEntityFeature.ARM_AWAY
)

ATTR_SYSTEM_SERIAL_NUMBER = "serial_number"
ATTR_SYSTEM_MODEL = "model"
ATTR_SYSTEM_READY = "ready"
ATTR_SYSTEM_CONNECTED = "connected"
ATTR_SYSTEM_SESSION_TOKEN = "session_token"
ATTR_SYSTEM_LAST_UPDATE = "last_update"
ATTR_CHANGED_BY = "changed_by"
ATTR_CHANGED_TIMESTAMP = "changed_timestamp"
ATTR_ALARMS = "alarm"

SCAN_INTERVAL = timedelta(seconds=7)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):
    """Set up the Visonic Alarm platform from a config entry."""

    hub = hass.data[DOMAIN][entry.entry_id]

    await hass.async_add_executor_job(
        hub.update
    )

    visonic_alarm = VisonicAlarm(
        hass,
        hub,
    )

    async_add_entities(
        [visonic_alarm],
        True,
    )

    def arm_event_listener(event):
        """Listen for arm state changes and update last event."""

        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if old_state is None or new_state is None:
            return

        if new_state.state in (
            STATE_UNKNOWN,
            "",
        ):
            return

        if (
            entity_id == visonic_alarm.entity_id
            and old_state.state != new_state.state
        ):
            state = new_state.state

            if state in (
                AlarmControlPanelState.ARMED_HOME.value,
                AlarmControlPanelState.ARMED_AWAY.value,
                AlarmControlPanelState.DISARMED.value,
            ):
                try:
                    last_event = hub.alarm.get_last_event(
                        timestamp_hour_offset=
                        visonic_alarm.event_hour_offset
                    )

                    if last_event:
                        visonic_alarm.update_last_event(
                            last_event.get("user"),
                            last_event.get("timestamp"),
                        )

                except Exception as err:
                    _LOGGER.debug(
                        "Visonic: no event to attribute yet (%s)",
                        err,
                    )

    entry.async_on_unload(
        hass.bus.async_listen(
            EVENT_STATE_CHANGED,
            arm_event_listener,
        )
    )


class VisonicAlarm(AlarmControlPanelEntity):
    """Representation of a Visonic Alarm control panel."""

    _attr_code_arm_required = False

    def __init__(
        self,
        hass: HomeAssistant,
        hub,
    ):
        """Initialize the alarm entity."""

        self._hass = hass
        self._hub = hub

        # Modern Home Assistant alarm entity state.
        # Do not write directly to self._state.
        self._attr_alarm_state: AlarmControlPanelState | None = None

        self._code = hub.config.get(
            CONF_USER_CODE
        )

        self._no_pin_required = hub.config.get(
            CONF_NO_PIN_REQUIRED,
            False,
        )

        self._changed_by = None
        self._changed_timestamp = None

        self._event_hour_offset = hub.config.get(
            CONF_EVENT_HOUR_OFFSET,
            0,
        )

        self._id = hub.alarm.serial_number

    @property
    def name(self):
        """Return the name of the alarm."""

        return "Visonic Alarm"

    @property
    def unique_id(self):
        """Return the unique ID of the alarm."""

        return self._id

    @property
    def state_attributes(self):
        """Return additional alarm attributes."""

        return {
            ATTR_SYSTEM_SERIAL_NUMBER:
                self._hub.alarm.serial_number,

            ATTR_SYSTEM_MODEL:
                self._hub.alarm.model,

            ATTR_SYSTEM_READY:
                self._hub.alarm.ready,

            ATTR_SYSTEM_CONNECTED:
                self._hub.alarm.connected,

            ATTR_CODE_FORMAT:
                self.code_format,

            ATTR_CHANGED_BY:
                self.changed_by,

            ATTR_CHANGED_TIMESTAMP:
                self._changed_timestamp,

            ATTR_ALARMS:
                self._hub.alarm.alarm,
        }

    @property
    def icon(self):
        """Return the icon for the current alarm state."""

        if (
            self._attr_alarm_state
            == AlarmControlPanelState.ARMED_AWAY
        ):
            return "mdi:shield-lock"

        if (
            self._attr_alarm_state
            == AlarmControlPanelState.ARMED_HOME
        ):
            return "mdi:shield-home"

        if (
            self._attr_alarm_state
            == AlarmControlPanelState.ARMED_NIGHT
        ):
            return "mdi:shield-moon"

        if (
            self._attr_alarm_state
            == AlarmControlPanelState.DISARMED
        ):
            return "mdi:shield-check"

        if (
            self._attr_alarm_state
            == AlarmControlPanelState.ARMING
        ):
            return "mdi:shield-outline"

        if (
            self._attr_alarm_state
            == AlarmControlPanelState.PENDING
        ):
            return "mdi:shield-half-full"

        if (
            self._attr_alarm_state
            == AlarmControlPanelState.TRIGGERED
        ):
            return "mdi:bell-alert"

        return "mdi:bell-ring"

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        """Return the current alarm state."""

        return self._attr_alarm_state

    @property
    def code_format(self):
        """Return the code format."""

        return (
            None
            if self._no_pin_required
            else "Number"
        )

    @property
    def changed_by(self):
        """Return who last changed the alarm."""

        return self._changed_by

    @property
    def changed_timestamp(self):
        """Return the timestamp of the last alarm change."""

        return self._changed_timestamp

    @property
    def event_hour_offset(self):
        """Return configured event-hour offset."""

        return self._event_hour_offset

    def update_last_event(
        self,
        user,
        timestamp,
    ):
        """Update information about the last alarm event."""

        self._changed_by = user
        self._changed_timestamp = timestamp

    def update(self):
        """Update alarm status from the hub."""

        self._hub.update()

        raw = self._hub.alarm.state

        _LOGGER.debug(
            "Visonic raw state: %s",
            raw,
        )

        if raw is None:
            self._attr_alarm_state = None
            return

        status = str(raw).strip().upper()

        _LOGGER.debug(
            "Visonic normalized state: %s",
            status,
        )

        mapping = {
            # Away
            "AWAY":
                AlarmControlPanelState.ARMED_AWAY,

            "ARMED_AWAY":
                AlarmControlPanelState.ARMED_AWAY,

            "ARM":
                AlarmControlPanelState.ARMED_AWAY,

            # Home / Stay
            "HOME":
                AlarmControlPanelState.ARMED_HOME,

            "STAY":
                AlarmControlPanelState.ARMED_HOME,

            "ARMED_HOME":
                AlarmControlPanelState.ARMED_HOME,

            # Night
            "NIGHT":
                AlarmControlPanelState.ARMED_NIGHT,

            "ARMED_NIGHT":
                AlarmControlPanelState.ARMED_NIGHT,

            # Disarmed
            "DISARM":
                AlarmControlPanelState.DISARMED,

            "DISARMED":
                AlarmControlPanelState.DISARMED,

            "READY":
                AlarmControlPanelState.DISARMED,

            "IDLE":
                AlarmControlPanelState.DISARMED,

            # Arming / exit delay
            "ARMING":
                AlarmControlPanelState.ARMING,

            "EXITDELAY":
                AlarmControlPanelState.ARMING,

            "EXIT_DELAY":
                AlarmControlPanelState.ARMING,

            # Entry delay / pending
            "ENTRYDELAY":
                AlarmControlPanelState.PENDING,

            "ENTRY_DELAY":
                AlarmControlPanelState.PENDING,

            "PENDING":
                AlarmControlPanelState.PENDING,

            # Alarm / triggered
            "ALARM":
                AlarmControlPanelState.TRIGGERED,

            "TRIGGERED":
                AlarmControlPanelState.TRIGGERED,
        }

        new_state = mapping.get(
            status
        )

        if new_state is None:
            _LOGGER.warning(
                "Unknown Visonic alarm state: %s",
                status,
            )

            self._attr_alarm_state = None
            return

        self._attr_alarm_state = new_state

        _LOGGER.debug(
            "Visonic Home Assistant alarm state: %s",
            self._attr_alarm_state,
        )

    @property
    def supported_features(self) -> int:
        """Return supported alarm features."""

        return SUPPORT_VISONIC

    def alarm_disarm(
        self,
        code=None,
    ):
        """Disarm the alarm."""

        if (
            not self._no_pin_required
            and code != self._code
        ):
            pn.create(
                self._hass,
                "You entered the wrong disarm code.",
                title="Disarm Failed",
            )

            return

        self._hub.alarm.disarm()

        sleep(1)

        self.update()

    def alarm_arm_home(
        self,
        code=None,
    ):
        """Arm the alarm in home mode."""

        if (
            not self._no_pin_required
            and code != self._code
        ):
            pn.create(
                self._hass,
                "You entered the wrong arm code.",
                title="Arm Failed",
            )

            return

        if self._hub.alarm.ready:

            self._hub.alarm.arm_home()

            sleep(1)

            self.update()

        else:

            pn.create(
                self._hass,
                (
                    "The alarm system is not in a ready state. "
                    "Maybe there are doors or windows open?"
                ),
                title="Arm Failed",
            )

    def alarm_arm_away(
        self,
        code=None,
    ):
        """Arm the alarm in away mode."""

        if (
            not self._no_pin_required
            and code != self._code
        ):
            pn.create(
                self._hass,
                "You entered the wrong arm code.",
                title="Unable to Arm",
            )

            return

        if self._hub.alarm.ready:

            self._hub.alarm.arm_away()

            sleep(1)

            self.update()

        else:

            pn.create(
                self._hass,
                (
                    "The alarm system is not in a ready state. "
                    "Maybe there are doors or windows open?"
                ),
                title="Unable to Arm",
            )
