# Changelog

All notable changes to SmartGrill will be documented in this file.

## [0.2.0-beta.1] - Unreleased

### Added

- Installable Progressive Web App
- Web Push subscriptions and test notifications
- Minimum and maximum temperature alerts for all five sensors
- Low-battery and Bluetooth-disconnection alerts
- Configurable hysteresis to prevent repeated notifications around a threshold
- Persistent VAPID keys, push subscriptions and alert settings

## [0.1.1] - Unreleased

### Added

- General-purpose README for new users
- `.gitignore`
- More robust installation and update scripts
- Validation for required configuration files
- Web-based settings page for Bluetooth, connection and probe-name settings

### Changed

- FastAPI application version aligned with the project version
- systemd service now uses host and port values from `.env`
- Update process now refreshes the systemd service definition
- Dashboard now uses the configured names for the ambient sensor and probes

## [0.1.0]

### Added

- Bluetooth connection to the ToGrill AT-02
- Live web dashboard
- REST status and health endpoints
- Automatic Bluetooth reconnect
- Automatic startup through systemd
- Raspberry Pi Zero W support
