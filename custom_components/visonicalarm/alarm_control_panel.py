"""
Interfaces with the Visonic Alarm control panel.
"""

import logging
from time import sleep
from datetime import timedelta

import homeassistant.components.alarm_control_panel as alarm
from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
import homeassistant.components.persistent_notification as pn
from homeassistant.const import (
    ATTR_CODE_FORMAT,
    EVENT_STATE_CHANGED,
    STATE_UNKNOWN,
)

# -------------------------------------------------------------
# Compatibility shim for old and new Home Assistant versions
# -------------------------------------------------------------
try:
    from homeassistant.components.alarm_control_panel import AlarmControlPanelState

    STATE_ALARM_DISARMED = AlarmControlPanelState.DISARMED
    STATE_ALARM_ARMED_HOME = AlarmControlPanelState.ARMED_HOME
    STATE_ALARM_ARMED_AWAY = AlarmControlPanelState.ARMED_AWAY
    STATE_ALARM_ARMED_NIGHT = AlarmControlPanelState.ARMED_NIGHT
    STATE_ALARM_TRIGGERED = AlarmControlPanelState.TRIGGERED
    STATE_ALARM_PENDING = AlarmControlPanelState.PENDING
    STATE_ALARM_ARMING = AlarmControlPanelState.ARMING
except Exception:
    from homeassistant.components.alarm_control_panel.const import (
        STATE_ALARM_DISARMED,
        STATE_ALARM_ARMED_HOME,
        STATE_ALARM_ARMED_AWAY,
        STATE_ALARM_ARMED_NIGHT,
        STATE_ALARM_TRIGGERED,
        STATE_ALARM_PENDING,
        STATE_ALARM_ARMING,
    )
    AlarmControlPanelState = None

from . import CONF_EVENT_HOUR_OFFSET, CONF_NO_PIN_REQUIRED, CONF_USER_CODE, HUB as hub

SUPPORT_VISONIC = (
    AlarmControlPanelEntityFeature.ARM_HOME |
    AlarmControlPanelEntityFeature.ARM_AWAY
)

_LOGGER = logging.getLogger(__name__)

ATTR_SYSTEM_SERIAL_NUMBER = "serial_number"
ATTR_SYSTEM_MODEL = "model"
ATTR_SYSTEM_READY = "ready"
ATTR_SYSTEM_CONNECTED = "connected"
ATTR_SYSTEM_SESSION_TOKEN = "session_token"
ATTR_SYSTEM_LAST_UPDATE = "last_update"
ATTR_CHANGED_BY = "changed_by"
ATTR_CHANGED_TIMESTAMP = "changed_timestamp"
ATTR_ALARMS = "alarm"

SCAN_INTERVAL = timedelta(seconds=10)


# =====================================================================
# Setup platform
# =====================================================================
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Visonic Alarm platform."""
    hub.update()
    visonic_alarm = VisonicAlarm(hass)
    add_devices([visonic_alarm])

    # Listen for changes to update last event info
    def arm_event_listener(event):
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if new_state is None or new_state.state in (STATE_UNKNOWN, ""):
            return

        if entity_id == "alarm_control_panel.visonic_alarm" and old_state and (
            old_state.state != new_state.state
        ):
            state = str(new_state.state).lower()
            if state in ("armed_home", "armed_away", "disarmed"):
                last_event = hub.alarm.get_last_event(
                    timestamp_hour_offset=visonic_alarm.event_hour_offset
                )
                visonic_alarm.update_last_event(
                    last_event["user"], last_event["timestamp"]
                )

    hass.bus.listen(EVENT_STATE_CHANGED, arm_event_listener)


# =====================================================================
# Main alarm class
# =====================================================================
class VisonicAlarm(AlarmControlPanelEntity):
    """Representation of a Visonic Alarm control panel."""

    _attr_code_arm_required = False

    def __init__(self, hass):
        self._hass = hass
        self._attr_state = STATE_UNKNOWN
        self._code = hub.config.get(CONF_USER_CODE)
        self._no_pin_required = hub.config.get(CONF_NO_PIN_REQUIRED)
        self._changed_by = None
        self._changed_timestamp = None
        self._event_hour_offset = hub.config.get(CONF_EVENT_HOUR_OFFSET)
        self._id = hub.alarm.serial_number

    # -----------------------------------------------------------------
    # Basic properties
    # -----------------------------------------------------------------
    @property
    def name(self):
        return "Visonic Alarm"

    @property
    def unique_id(self):
        return self._id

    @property
    def extra_state_attributes(self):
        return {
            ATTR_SYSTEM_SERIAL_NUMBER: hub.alarm.serial_number,
            ATTR_SYSTEM_MODEL: hub.alarm.model,
            ATTR_SYSTEM_READY: hub.alarm.ready,
            ATTR_SYSTEM_CONNECTED: hub.alarm.connected,
            ATTR_SYSTEM_SESSION_TOKEN: hub.alarm.session_token,
            ATTR_SYSTEM_LAST_UPDATE: hub.last_update,
            ATTR_CODE_FORMAT: self.code_format,
            ATTR_CHANGED_BY: self.changed_by,
            ATTR_CHANGED_TIMESTAMP: self._changed_timestamp,
            ATTR_ALARMS: hub.alarm.alarm,
        }

    @property
    def icon(self):
        st = self._attr_state
        if st == STATE_ALARM_ARMED_AWAY:
            return "mdi:shield-lock"
        if st == STATE_ALARM_ARMED_HOME:
            return "mdi:shield-home"
        if st == STATE_ALARM_DISARMED:
            return "mdi:shield-check"
        if st == STATE_ALARM_ARMING:
            return "mdi:shield-outline"
        return "hass:bell-ring"

    @property
    def code_format(self):
        return None if self._no_pin_required else "Number"

    @property
    def changed_by(self):
        return self._changed_by

    @property
    def changed_timestamp(self):
        return self._changed_timestamp

    @property
    def event_hour_offset(self):
        return self._event_hour_offset

    # -----------------------------------------------------------------
    # Update event info
    # -----------------------------------------------------------------
    def update_last_event(self, user, timestamp):
        self._changed_by = user
        self._changed_timestamp = timestamp

    # =================================================================
    # Update alarm state (THIS IS THE IMPORTANT PART)
    # =================================================================
    def update(self):
        """Update alarm status from the Hub."""
        hub.update()

        raw = hub.alarm.state

        # Debug log to learn what the panel is REALLY sending
        _LOGGER.warning(f"Visonic raw state: {raw}")

        if raw is None:
            self._attr_state = STATE_UNKNOWN
            return

        # Normalize
        status = str(raw).strip().upper()
        _LOGGER.debug(f"Visonic normalized state: {status}")

        # UNIVERSAL STATE MAPPING (handles many different panel firmwares)
        mapping = {
            "AWAY": STATE_ALARM_ARMED_AWAY,
            "ARMED_AWAY": STATE_ALARM_ARMED_AWAY,
            "ARM": STATE_ALARM_ARMED_AWAY,
            "ARM_AWAY": STATE_ALARM_ARMED_AWAY,

            "HOME": STATE_ALARM_ARMED_HOME,
            "STAY": STATE_ALARM_ARMED_HOME,
            "ARMED_HOME": STATE_ALARM_ARMED_HOME,
            "ARM_HOME": STATE_ALARM_ARMED_HOME,

            "DISARM": STATE_ALARM_DISARMED,
            "DISARMED": STATE_ALARM_DISARMED,
            "READY": STATE_ALARM_DISARMED,
            "IDLE": STATE_ALARM_DISARMED,

            "ARMING": STATE_ALARM_ARMING,
            "EXITDELAY": STATE_ALARM_ARMING,

            "ENTRYDELAY": STATE_ALARM_PENDING,
            "PENDING": STATE_ALARM_PENDING,

            "ALARM": STATE_ALARM_TRIGGERED,
            "TRIGGERED": STATE_ALARM_TRIGGERED,
        }

        self._attr_state = mapping.get(status, STATE_UNKNOWN)

    # =================================================================
    # Commands
    # =================================================================
    @property
    def supported_features(self):
        return SUPPORT_VISONIC

    def alarm_disarm(self, code=None):
        if not self._no_pin_required and code != self._code:
            pn.create(self._hass,
                "You entered the wrong disarm code.",
                title="Disarm Failed"
            )
            return

        hub.alarm.disarm()
        sleep(1)
        self.update()

    def alarm_arm_home(self, code=None):
        if not self._no_pin_required and code != self._code:
            pn.create(self._hass,
                "You entered the wrong arm code.",
                title="Arm Failed"
            )
            return

        if hub.alarm.ready:
            hub.alarm.arm_home()
            sleep(1)
            self.update()
        else:
            pn.create(
                self._hass,
                "The alarm system is not ready. Doors/windows open?",
                title="Arm Failed"
            )

    def alarm_arm_away(self, code=None):
        if not self._no_pin_required and code != self._code:
            pn.create(self._hass,
                "You entered the wrong arm code.",
                title="Unable to Arm"
            )
            return

        if hub.alarm.ready:
            hub.alarm.arm_away()
            sleep(1)
            self.update()
        else:
            pn.create(
                self._hass,
                "The alarm system is not ready. Doors/windows open?",
                title="Unable to Arm"
            )
