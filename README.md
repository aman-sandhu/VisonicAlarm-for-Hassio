# Visonic/Bentel/Tyco Alarm for Home Assistant

[![HACS](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

<a href="https://www.buymeacoffee.com/4nd3rs" target="_blank">
  <img src="https://cdn.buymeacoffee.com/buttons/default-black.png"
       width="150px"
       height="35px"
       alt="Buy Me A Coffee">
</a>

Home Assistant custom integration for Visonic/Bentel/Tyco alarm systems using the Tyco Monitor API.

## Credits

A big thank you to **And3rsL**, the original author of this Home Assistant integration and the VisonicAlarm2 Python library.

This project is based on his original **VisonicAlarm-for-Hassio** work. The core Visonic/Tyco API implementation and the foundation of this integration are his work.

This fork builds on that foundation with updated Home Assistant compatibility, GUI/config-entry setup, automatic YAML migration, and configuration through the Home Assistant UI.

Original projects:

- VisonicAlarm-for-Hassio: https://github.com/And3rsL/VisonicAlarm-for-Hassio
- VisonicAlarm2: https://github.com/And3rsL/VisonicAlarm2

The **Buy Me a Coffee** button above links to And3rsL's support page.

Many thanks to **And3rsL** for creating and sharing the original projects.

## Features

- Home Assistant GUI configuration
- Alarm Control Panel entity
- Arm Home
- Arm Away
- Disarm
- Door/window contact sensors
- Motion/curtain sensor support
- Configuration through Home Assistant
- Automatic import of existing YAML configuration
- HACS installation and updates

The integration polls the alarm API periodically for alarm and device status.

## Requirements

This integration uses the `visonicalarm2` Python library.

It has primarily been tested with a Visonic PowerMaster 10 using a PowerLink 3 Ethernet module.

Other compatible Visonic/Bentel/Tyco systems using the same API may also work, but have not necessarily been tested.

The account used with the integration should be the **MASTER USER**, and the alarm panel must already be registered to that account.

## Installation

### HACS

Install **Visonic/Bentel/Tyco Alarm System** through HACS.

After installation, restart Home Assistant.

Then go to:

**Settings → Devices & services → Add Integration**

Search for:

**Visonic Alarm**

Select the integration and enter your alarm details.

## GUI Configuration

The integration can be configured through the Home Assistant user interface.

During initial setup you will be asked for:

- **Host** — your alarm provider API host
- **App ID** — application UUID used by the Visonic API
- **User Code** — alarm user code
- **Email** — account email address
- **Password** — account password
- **Panel ID** — alarm panel ID
- **Partition** — alarm partition
- **Name** — name used for the integration
- **No PIN required** — allow alarm commands without entering a PIN
- **Event hour offset** — optional time adjustment for alarm events

A typical host looks similar to:

```text
visonic.tycomonitor.com
```

For systems using the original configuration, the partition is commonly:

```text
-1
```

## Existing YAML Users

Older versions of this integration were configured through `configuration.yaml`.

For example:

```yaml
visonicalarm:
  host: YOURALARMCOMPANY.tycomonitor.com
  panel_id: 123456
  user_code: 1234
  app_id: 00000000-0000-0000-0000-000000000000
  user_email: example@email.com
  user_password: yourpassword
  partition: -1
  no_pin_required: false
```

Version **v2026.9.1** and later supports Home Assistant config entries and GUI configuration.

When Home Assistant starts with an existing `visonicalarm:` YAML configuration, the integration automatically imports those settings into a Home Assistant config entry.

After the import, go to:

**Settings → Devices & services → Visonic Alarm**

Confirm that the alarm and sensor entities are present and working correctly.

Once the migration has been confirmed, the old `visonicalarm:` section can be removed from `configuration.yaml`.

Existing Home Assistant entity IDs and history should be preserved during the migration.

## Changing Settings

Go to:

**Settings → Devices & services → Visonic Alarm**

Open the existing Visonic hub and select **Configure**.

The following settings can currently be changed through the Configure screen:

- Partition
- Name
- No PIN required
- Event hour offset

Saving configuration changes automatically reloads the integration.

During the reload, the alarm and sensor entities may briefly show **Unavailable** while the integration reconnects. They should return to their current states once the connection has been restored.

## Entities

The integration creates an `alarm_control_panel` entity representing the alarm system.

It also creates entities for supported alarm devices, including:

- Door/window contacts
- Motion sensors
- Curtain sensors

Existing installations should retain their existing Home Assistant entity IDs when migrating from YAML configuration.

## Alarm Controls

The Home Assistant Alarm Control Panel supports:

- **Disarm**
- **Arm Home**
- **Arm Away**

Alarm commands are sent to the Visonic API and the alarm state is then refreshed in Home Assistant.

## App ID

The App ID is a UUID used when connecting to the Visonic API.

An example UUID looks like:

```text
00000000-0000-0000-0000-000000000000
```

Existing users migrating from YAML should continue using their existing App ID.

## Security

Your Visonic account credentials are stored by Home Assistant as part of the integration configuration.

Do not publish or share your:

- Password
- User code
- Panel ID
- App ID
- Home Assistant configuration containing these credentials

For legacy YAML configurations, Home Assistant `secrets.yaml` can be used to keep credentials out of `configuration.yaml`.

## Compatibility

This integration communicates with an API used by Visonic/Bentel/Tyco alarm applications.

Visonic does not publish or officially support this REST API. Changes made by Visonic, Tyco, the alarm provider, or the API service may therefore affect the integration.

This integration is not an official Visonic/Bentel/Tyco product.

## Python Library

The integration uses the **VisonicAlarm2** Python library originally developed by **And3rsL**:

https://github.com/And3rsL/VisonicAlarm2

The required Python package is installed automatically by Home Assistant.

## Disclaimer

This software is provided without warranty.

The integration is not supported or endorsed by Visonic, Bentel, or Tyco.

You are responsible for determining whether this integration is appropriate for use with your alarm system. The developers and contributors accept no liability for loss, damage, security incidents, or other consequences resulting from its use.

## Screenshot

![Alarm Panel dialog](HomeAssistantArmDialog2.png)

## Version

Current stable GUI/config-entry release:

**v2026.9.4**
