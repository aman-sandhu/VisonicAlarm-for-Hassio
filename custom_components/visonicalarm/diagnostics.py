"""Diagnostics support for Visonic Alarm."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import (
    CONF_APP_ID,
    CONF_PANEL_ID,
    CONF_USER_CODE,
    CONF_USER_EMAIL,
    CONF_USER_PASSWORD,
    DOMAIN,
)

TO_REDACT = {
    CONF_APP_ID,
    CONF_PANEL_ID,
    CONF_USER_CODE,
    CONF_USER_EMAIL,
    CONF_USER_PASSWORD,
}


SAFE_LOCATION_KEYS = {
    "id",
    "name",
    "zone",
    "zone_id",
    "zone_number",
    "device_number",
    "location",
    "location_id",
}


SAFE_RAW_DEVICE_KEYS = {
    "id",
    "name",
    "device_type",
    "subtype",
    "zone",
    "zone_id",
    "zone_number",
    "device_number",
    "zone_type",
    "location",
    "location_id",
    "partitions",
}


def _safe_records(
    records: Any,
    allowed_keys: set[str],
) -> list[dict[str, Any]]:
    """Return allowlisted fields from API records."""

    if not isinstance(records, list):
        return []

    return [
        {
            key: record.get(key)
            for key in allowed_keys
            if key in record
        }
        for record in records
        if isinstance(record, dict)
    ]


def _record_keys(records: Any) -> list[list[str]]:
    """Return sorted key names only from API records."""

    if not isinstance(records, list):
        return []

    return [
        sorted(record.keys())
        for record in records
        if isinstance(record, dict)
    ]


def _trait_keys(records: Any) -> list[dict[str, Any]]:
    """Return device numbers and nested trait key names only."""

    if not isinstance(records, list):
        return []

    result = []

    for record in records:
        if not isinstance(record, dict):
            continue

        traits = record.get("traits")

        if isinstance(traits, dict):
            keys = sorted(traits.keys())
        elif isinstance(traits, list):
            keys = sorted(
                {
                    key
                    for item in traits
                    if isinstance(item, dict)
                    for key in item.keys()
                }
            )
        else:
            keys = []

        result.append(
            {
                "device_number": record.get("device_number"),
                "device_type": record.get("device_type"),
                "trait_keys": keys,
            }
        )

    return result


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a Visonic Alarm config entry."""

    hub = hass.data[DOMAIN][entry.entry_id]
    alarm = hub.alarm

    locations = await hass.async_add_executor_job(
        alarm.get_locations
    )

    raw_devices = await hass.async_add_executor_job(
        alarm.get_raw_devices
    )

    devices = []

    for index, device in enumerate(alarm.devices, start=1):
        devices.append(
            {
                "index": index,
                "device_type": device.device_type,
                "subtype": device.subtype,
                "zone": device.zone,
                "partitions": device.partitions,
                "device_number": device.device_number,
            }
        )

    return {
        "config_entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(dict(entry.options), TO_REDACT),
        },
        "hub": {
            "last_update": (
                hub.last_update.isoformat()
                if hub.last_update is not None
                else None
            ),
        },
        "panel": {
            "model": alarm.model,
            "ready": alarm.ready,
            "state": alarm.state,
            "alarm_active": alarm.alarm,
            "connected": alarm.connected,
            "device_count": len(alarm.devices),
        },
        "devices": devices,
        "locations": _safe_records(
            locations,
            SAFE_LOCATION_KEYS,
        ),
        "raw_devices": _safe_records(
            raw_devices,
            SAFE_RAW_DEVICE_KEYS,
        ),
        "raw_device_keys": _record_keys(raw_devices),
        "raw_device_trait_keys": _trait_keys(raw_devices),
    }
