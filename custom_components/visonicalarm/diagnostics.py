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

SAFE_EVENT_KEYS = {
    "event",
    "id",
    "type_id",
    "label",
    "description",
    "datetime",
    "video",
    "device_type",
    "zone",
    "partitions",
}

SAFE_ALARM_KEYS = {
    "event",
    "id",
    "type_id",
    "label",
    "description",
    "datetime",
    "device_type",
    "zone",
    "partitions",
}

SAFE_TROUBLE_KEYS = {
    "device_type",
    "trouble_type",
    "zone",
    "zone_type",
    "partitions",
}


def _safe_records(
    records: Any,
    allowed_keys: set[str],
    *,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return allowlisted fields from API records."""

    if not isinstance(records, list):
        return []

    safe_records = []

    selected_records = records[-limit:] if limit else records

    for record in selected_records:
        if not isinstance(record, dict):
            continue

        safe_records.append(
            {
                key: record.get(key)
                for key in allowed_keys
                if key in record
            }
        )

    return safe_records


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> dict[str, Any]:
    """Return diagnostics for a Visonic Alarm config entry."""

    hub = hass.data[DOMAIN][entry.entry_id]
    alarm = hub.alarm

    devices = []

    for index, device in enumerate(alarm.devices, start=1):
        devices.append(
            {
                "index": index,
                "device_id": device.id,
                "device_type": device.device_type,
                "subtype": device.subtype,
                "zone": device.zone,
                "partitions": device.partitions,
                "device_number": device.device_number,
            }
        )

    recent_events = await hass.async_add_executor_job(
        alarm.get_events
    )

    current_alarms = await hass.async_add_executor_job(
        alarm.get_alarms
    )

    current_troubles = await hass.async_add_executor_job(
        alarm.get_troubles
    )

    return {
        "config_entry": {
            "data": async_redact_data(
                dict(entry.data),
                TO_REDACT,
            ),
            "options": async_redact_data(
                dict(entry.options),
                TO_REDACT,
            ),
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
        "recent_events": _safe_records(
            recent_events,
            SAFE_EVENT_KEYS,
            limit=10,
        ),
        "current_alarms": _safe_records(
            current_alarms,
            SAFE_ALARM_KEYS,
        ),
        "current_troubles": _safe_records(
            current_troubles,
            SAFE_TROUBLE_KEYS,
        ),
    }
