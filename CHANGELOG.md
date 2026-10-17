## v2026.10.0 - 2026-10-17

### Added
- Added a new **Visonic Alarm Trouble** sensor.
- Added support for current panel trouble conditions reported by the Visonic cloud API.
- Low-battery troubles now show the affected location, zone, zone type, device type, partition, and raw trouble details as sensor attributes.
- Multiple simultaneous troubles are supported through the sensor attributes.

### Changed
- The integration now refreshes panel trouble information during the normal hub update cycle.
- Added a public `troubles` property to the Visonic system wrapper.

### Tested
- Confirmed a real `LOW_BATTERY` trouble from **Family room / Zone 4** was detected correctly.
- New `sensor.visonic_alarm_trouble` entity loaded successfully in Home Assistant.
- Python syntax checks passed for all modified integration files.
- Home Assistant restarted successfully with the new trouble sensor active.