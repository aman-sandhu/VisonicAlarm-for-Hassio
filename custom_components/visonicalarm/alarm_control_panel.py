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
    AlarmControlPanelState,
)
import homeassistant.components.persistent_notification as pn
from homeassistant.const import (
    ATTR_CODE_FORMAT,
    EVENT_STATE_CHANGED,
    STATE_UNKNOWN,
)

from . import CONF_EVENT_HOUR_OFFSET, CONF_NO_PIN_REQUIRED, CONF_USER_CODE, HUB as hub

SUPPORT_VISONIC = (
    AlarmControlPanelEntityFeature.ARM_HOME |
    AlarmControlPanelEntityFeature.ARM_AWAY
)

_LOGGER = logging.getLogger(__name__)

ATTR_SYSTEM_SERIAL_NUMBER = 'serial_number'
ATTR_SYSTEM_MODEL = 'model'
ATTR_SYSTEM_READY = 'ready'
ATTR_SYSTEM_CONNECTED = 'connected'
ATTR_SYSTEM_SESSION_TOKEN = 'session_token'
ATTR_SYSTEM_LAST_UPDATE = 'last_update'
ATTR_CHANGED_BY = 'changed_by'
ATTR_CHANGED_TIMESTAMP = 'changed_timestamp'
ATTR_ALARMS = 'alarm'

SCAN_INTERVAL = timedelta(seconds=10)


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Set up the Visonic Alarm platform."""
    hub.update()
    visonic_alarm = VisonicAlarm(hass)
    add_devices([visonic_alarm])

    def arm_event_listener(event):
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")

        if new_state is None or new_state.state in (STATE_UNKNOWN, ''):
            return

        if (
            entity_id == "alarm_control_panel.visonic_alarm"
            and old_state.state is not new_state.state
        ):
            state = new_state.state
            if state in (
                AlarmControlPanelState.ARMED_HOME,
                AlarmControlPanelState.ARMED_AWAY,
                AlarmControlPanelState.DISARMED,
            ):
                last_event = hub.alarm.get_last_event(
                    timestamp_hour_offset=visonic_alarm.event_hour_offset
                )
                visonic_alarm.update_last_event(
                    last_event["user"], last_event["timestamp"]
                )

    hass.bus.listen(EVENT_STATE_CHANGED, arm_event_listener)


class VisonicAlarm(AlarmControlPanelEntity):
    """Representation of a Visonic Alarm control panel."""
    _attr_code_arm_required = False

    def __init__(self, hass):
        """Initialize the Visonic Alarm panel."""
        self._hass = hass
        self._attr_state = STATE_UNKNOWN
        self._code = hub.config.get(CONF_USER_CODE)
        self._no_pin_required = hub.config.get(CONF_NO_PIN_REQUIRED)
        self._changed_by = None
        self._changed_timestamp = None
        self._event_hour_offset = hub.config.get(CONF_EVENT_HOUR_OFFSET)
        self._id = hub.alarm.serial_number

    @property
    def name(self):
        return "Visonic Alarm"

    @property
    def unique_id(self):
        return self._id

    @property
    def state_attributes(self):
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
        """Return icon for current state."""
        if self._attr_state == AlarmControlPanelState.ARMED_AWAY:
            return "mdi:shield-lock"
        elif self._attr_state == AlarmControlPanelState.ARMED_HOME:
            return "mdi:shield-home"
        elif self._attr_state == AlarmControlPanelState.DISARMED:
            return "mdi:shield-check"
        elif self._attr_state == AlarmControlPanelState.ARMING:
            return "mdi:shield-outline"
        else:
            return "hass:bell-ring"

    @property
    def code_format(self):
        if self._no_pin_required:
            return None
        return "Number"

    @property
    def changed_by(self):
        return self._changed_by

    @property
    def changed_timestamp(self):
        return self._changed_timestamp

    @property
    def event_hour_offset(self):
        return self._event_hour_offset

    def update_last_event(self, user, timestamp):
        self._changed_by = user
        self._changed_timestamp = timestamp

    def update(self):
        """Update alarm status."""
        hub.update()
        status = hub.alarm.state

        if status == "AWAY":
            self._attr_state = AlarmControlPanelState.ARMED_AWAY
        elif status == "HOME":
            self._attr_state = AlarmControlPanelState.ARMED_HOME
        elif status == "DISARM":
            self._attr_state = AlarmControlPanelState.DISARMED
        elif status == "ARMING":
            self._attr_state = AlarmControlPanelState.ARMING
        elif status == "ENTRYDELAY":
            self._attr_state = AlarmControlPanelState.PENDING
        elif status == "ALARM":
            self._attr_state = AlarmControlPanelState.TRIGGERED
        else:
            self._attr_state = status

    @property
    def supported_features(self):
        return SUPPORT_VISONIC

    def alarm_disarm(self, code=None):
        if not self._no_pin_required and code != self._code:
            pn.create(self._hass, "You entered the wrong disarm code.", title="Disarm Failed")
            return

        hub.alarm.disarm()
        sleep(1)
        self.update()

    def alarm_arm_home(self, code=None):
        if not self._no_pin_required and code != self._code:
            pn.create(self._hass, "You entered the wrong arm code.", title="Arm Failed")
            return

        if hub.alarm.ready:
            hub.alarm.arm_home()
            sleep(1)
            self.update()
        else:
            pn.create(
                self._hass,
                "The alarm system is not in a ready state. Maybe there are doors or windows open?",
                title="Arm Failed",
            )

    def alarm_arm_away(self, code=None):
        if not self._no_pin_required and code != self._code:
            pn.create(self._hass, "You entered the wrong arm code.", title="Unable to Arm")
            return

        if hub.alarm.ready:
            hub.alarm.arm_away()
            sleep(1)
            self.update()
        else:
            pn.create(
                self._hass,
                "The alarm system is not in a ready state. Maybe there are doors or windows open?",
                title="Unable to Arm",
            )
