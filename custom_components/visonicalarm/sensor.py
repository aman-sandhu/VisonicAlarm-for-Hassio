"""Interfaces with the Visonic Alarm sensors."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    STATE_CLOSED,
    STATE_OFF,
    STATE_ON,
    STATE_OPEN,
    STATE_UNKNOWN,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import Entity

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)

STATE_ALARM_ARMING_EXIT_DELAY_HOME = "arming_exit_delay_home"
STATE_ALARM_ARMING_EXIT_DELAY_AWAY = "arming_exit_delay_away"
STATE_ALARM_ENTRY_DELAY = "entry_delay"

STATE_ATTR_SYSTEM_NAME = "system_name"
STATE_ATTR_SYSTEM_SERIAL_NUMBER = "serial_number"
STATE_ATTR_SYSTEM_MODEL = "model"
STATE_ATTR_SYSTEM_READY = "ready"
STATE_ATTR_SYSTEM_ACTIVE = "active"
STATE_ATTR_SYSTEM_CONNECTED = "connected"

CONTACT_ATTR_ZONE = "zone"
CONTACT_ATTR_NAME = "name"
CONTACT_ATTR_DEVICE_TYPE = "device_type"
CONTACT_ATTR_SUBTYPE = "subtype"

SCAN_INTERVAL = timedelta(seconds=10)

KNOWN_MOTION_SUBTYPES = {
    "FLAT_PIR_SMART",
}


def _is_motion_subtype(subtype: str) -> bool:
    """Return whether a Visonic subtype represents a motion sensor."""

    return (
        "MOTION" in subtype
        or "CURTAIN" in subtype
        or subtype in KNOWN_MOTION_SUBTYPES
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
):
    """Set up Visonic Alarm sensors from a config entry."""

    hub = hass.data[DOMAIN][entry.entry_id]

    await hass.async_add_executor_job(
        hub.update
    )

    entities = []

    for device in hub.alarm.devices:
        if device is None:
            continue

        if device.subtype is None:
            continue

        if (
            "CONTACT" in device.subtype
            or _is_motion_subtype(device.subtype)
        ):
            _LOGGER.debug(
                "New device found [Type:%s] [ID:%s]",
                device.subtype,
                device.id,
            )

            entities.append(
                VisonicAlarmContact(
                    hub,
                    device.id,
                )
            )

    async_add_entities(
        entities,
        True,
    )


class VisonicAlarmContact(Entity):
    """Implementation of a Visonic Alarm contact sensor."""

    def __init__(
        self,
        hub,
        contact_id,
    ):
        """Initialize the sensor."""

        self._hub = hub
        self._state = STATE_UNKNOWN
        self._alarm = hub.alarm
        self._id = contact_id
        self._name = None
        self._zone = None
        self._device_type = None
        self._subtype = None

    @property
    def name(self):
        """Return the name of the sensor."""

        return str(self._name)

    @property
    def unique_id(self):
        """Return a unique ID."""

        return self._id

    @property
    def state_attributes(self):
        """Return sensor attributes."""

        return {
            CONTACT_ATTR_ZONE: self._zone,
            CONTACT_ATTR_NAME: self._name,
            CONTACT_ATTR_DEVICE_TYPE: self._device_type,
            CONTACT_ATTR_SUBTYPE: self._subtype,
        }

    @property
    def icon(self):
        """Return the icon."""

        if self._zone and "24H" in self._zone:
            if self._state == STATE_CLOSED:
                return "mdi:hours-24"

            if self._state == STATE_OPEN:
                return "mdi:alarm-light"

        elif self._state == STATE_CLOSED:
            return "mdi:door-closed"

        elif self._state == STATE_OPEN:
            return "mdi:door-open"

        elif self._state == STATE_OFF:
            return "mdi:motion-sensor-off"

        elif self._state == STATE_ON:
            return "mdi:motion-sensor"

        return None

    @property
    def state(self):
        """Return the current state."""

        return self._state

    def update(self):
        """Get the latest data."""

        try:
            self._hub.update()

            device = self._alarm.get_device_by_id(
                self._id
            )

            if device is None:
                _LOGGER.warning(
                    "Device could not be found: %s",
                    self._id,
                )
                self._state = STATE_UNKNOWN
                return

            status = device.state

            if status is None:
                _LOGGER.warning(
                    "Device state unavailable: %s",
                    self._id,
                )
                self._state = STATE_UNKNOWN
                return

            if status == "opened":
                self._state = STATE_OPEN

            elif status == "closed":
                self._state = STATE_CLOSED

            elif _is_motion_subtype(device.subtype):
                alarm_state = self._alarm.state
                alarm_zone = device.zone or ""

                if alarm_state in (
                    "DISARM",
                    "ARMING",
                ):
                    if "24H" in alarm_zone:
                        self._state = STATE_ON
                    else:
                        self._state = STATE_OFF

                elif alarm_state == "HOME":
                    if "INTERIOR" in alarm_zone:
                        self._state = STATE_OFF
                    else:
                        self._state = STATE_ON

                elif alarm_state in (
                    "AWAY",
                    "DISARMING",
                ):
                    self._state = STATE_ON

                else:
                    self._state = STATE_UNKNOWN

            else:
                self._state = STATE_UNKNOWN

            self._zone = device.zone
            self._name = device.name
            self._device_type = device.device_type
            self._subtype = device.subtype

            _LOGGER.debug(
                "Visonic device %s state updated to %s",
                self._id,
                self._state,
            )

        except OSError as error:
            _LOGGER.warning(
                "Could not update device information: %s",
                error,
            )
