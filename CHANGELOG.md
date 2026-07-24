# Changelog

All notable changes to SmartGrill will be documented in this file.

## [0.1.1] - Unreleased

### Added

- General-purpose README for new users
- `.gitignore`
- More robust installation and update scripts
- Validation for required configuration files

### Changed

- FastAPI application version aligned with the project version
- systemd service now uses host and port values from `.env`
- Update process now refreshes the systemd service definition

## [0.1.0]

### Added

- Bluetooth connection to the ToGrill AT-02
- Live web dashboard
- REST status and health endpoints
- Automatic Bluetooth reconnect
- Automatic startup through systemd
- Raspberry Pi Zero W support
