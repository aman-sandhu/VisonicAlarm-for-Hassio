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


def _zone_locations(records: Any) -> list[dict[str, Any]]:
    """Return zone numbers and friendly locations from device traits."""

    if not isinstance(records, list):
        return []

    result = []

    for record in records:
        if not isinstance(record, dict):
            continue

        if record.get("device_type") != "ZONE":
            continue

        traits = record.get("traits")
        location = None

        if isinstance(traits, dict):
            location = traits.get("location")

        result.append(
            {
                "device_number": record.get("device_number"),
                "device_id": record.get("id"),
                "location": location,
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
        "zone_locations": _zone_locations(raw_devices),
    }
