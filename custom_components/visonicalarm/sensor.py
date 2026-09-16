"""Interfaces with the Visonic Alarm sensors."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.components.sensor import SensorEntity
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

LAST_ALARM_TRIGGER_NAME = "Visonic Alarm Last Alarm Trigger"
LAST_ALARM_TRIGGER_ICON = "mdi:alarm-light"
LAST_ALARM_TRIGGER_UNIQUE_ID_SUFFIX = "last_alarm_trigger"

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


def _build_zone_device_map(raw_devices) -> dict[int, dict]:
    """Build a mapping of panel zone numbers to Visonic zone metadata."""

    zone_devices = {}

    if not isinstance(raw_devices, list):
        return zone_devices

    for record in raw_devices:
        if not isinstance(record, dict):
            continue

        if record.get("device_type") != "ZONE":
            continue

        device_number = record.get("device_number")

        try:
            zone_number = int(device_number)
        except (TypeError, ValueError):
            continue

        traits = record.get("traits")
        location = None

        if isinstance(traits, dict):
            location_record = traits.get("location")
            if isinstance(location_record, dict):
                location = location_record.get("name")
            elif isinstance(location_record, str):
                location = location_record

        zone_devices[zone_number] = {
            "device_id": record.get("id"),
            "location": location,
        }

    return zone_devices


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

    try:
        raw_devices = await hass.async_add_executor_job(
            hub.alarm.get_raw_devices
        )
        zone_device_map = _build_zone_device_map(raw_devices)
        device_location_map = {
            data.get("device_id"): data.get("location")
            for data in zone_device_map.values()
            if data.get("device_id") is not None
        }
    except Exception as error:  # noqa: BLE001
        _LOGGER.warning(
            "Could not load Visonic zone location mapping: %s",
            error,
        )
        zone_device_map = {}
        device_location_map = {}

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
                    device_location_map.get(device.id),
                )
            )

    entities.append(
        VisonicLastAlarmTrigger(
            hub,
            entry.entry_id,
            zone_device_map,
        )
    )

    async_add_entities(
        entities,
        True,
    )


class VisonicLastAlarmTrigger(SensorEntity):
    """Representation of the most recent Visonic zone alarm trigger."""

    _attr_icon = LAST_ALARM_TRIGGER_ICON
    _attr_name = LAST_ALARM_TRIGGER_NAME

    def __init__(
        self,
        hub,
        entry_id: str,
        zone_device_map: dict[int, dict],
    ):
        """Initialize the last alarm trigger sensor."""

        self._hub = hub
        self._alarm = hub.alarm
        self._zone_device_map = zone_device_map
        self._attr_unique_id = (
            f"{entry_id}_{LAST_ALARM_TRIGGER_UNIQUE_ID_SUFFIX}"
        )
        self._attr_native_value = None
        self._attr_extra_state_attributes = {}

    def update(self):
        """Update the most recent alarm-trigger information."""

        events = self._alarm.get_events()

        if not isinstance(events, list):
            return

        alarm_event = None

        for event in reversed(events):
            if not isinstance(event, dict):
                continue

            if event.get("device_type") != "ZONE":
                continue

            if (
                event.get("type_id") == 1
                or event.get("label") == "BURGLER"
            ):
                alarm_event = event
                break

        if alarm_event is None:
            return

        zone = alarm_event.get("zone")

        try:
            zone_number = int(zone)
        except (TypeError, ValueError):
            return

        zone_device = self._zone_device_map.get(
            zone_number,
            {},
        )

        location = zone_device.get("location")
        self._attr_native_value = location or f"Zone {zone_number}"

        partitions = alarm_event.get("partitions")
        partition = None

        if isinstance(partitions, list) and partitions:
            partition = partitions[0]

        self._attr_extra_state_attributes = {
            "zone": zone_number,
            "device_id": zone_device.get("device_id"),
            "event_type": alarm_event.get("label"),
            "description": alarm_event.get("description"),
            "partition": partition,
            "timestamp": alarm_event.get("datetime"),
            "event_id": alarm_event.get("event"),
        }


class VisonicAlarmContact(Entity):
    """Implementation of a Visonic Alarm contact sensor."""

    def __init__(
        self,
        hub,
        contact_id,
        location=None,
    ):
        """Initialize the sensor."""

        self._hub = hub
        self._state = STATE_UNKNOWN
        self._alarm = hub.alarm
        self._id = contact_id
        self._location = location
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

            if "CONTACT" in device.subtype:
                sensor_type = "Contact"
            elif _is_motion_subtype(device.subtype):
                sensor_type = "Motion"
            else:
                sensor_type = "Sensor"

            if self._location:
                self._name = f"{self._location} {sensor_type}"
            elif device.name:
                self._name = device.name
            else:
                self._name = f"Visonic Alarm {self._id}"

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
