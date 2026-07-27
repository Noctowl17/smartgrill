# SmartGrill 1.0.0

SmartGrill 1.0 is the first stable release of the lightweight web dashboard
and REST API for the ToGrill AT-02 Bluetooth BBQ thermometer. It turns a
Raspberry Pi into a continuously available grill monitor with automatic
reconnection, configurable probes and optional push notifications.

## Highlights

- Live temperature dashboard for the ambient sensor and four probes
- Custom names for every sensor
- Automatic Bluetooth reconnection and stale-data detection
- Installable Progressive Web App for desktop and mobile devices
- Minimum and maximum temperature alerts for all five sensors
- Optional low-battery and Bluetooth-disconnection alerts
- Configurable repeat interval for notifications while a temperature remains
  outside its limits
- Web Push subscriptions, alert settings and VAPID keys stored across restarts
- Reliable PWA updates that refresh cached JavaScript before using offline
  assets
- REST status, settings and health endpoints for integrations such as Homey
- Automatic startup and service management through systemd
- Installation and update scripts tailored for Raspberry Pi OS, including
  Raspberry Pi Zero W support

## Installation

For a new installation:

```bash
git clone https://github.com/Noctowl17/smartgrill.git
cd smartgrill
cp .env.example .env
nano .env
sudo bash install.sh
```

Set `TOGRILL_ADDRESS` in `.env` to the Bluetooth MAC address of the
thermometer before running the installer.

## Upgrading

Existing installations can be upgraded from the repository directory:

```bash
./update.sh
```

The update script downloads the latest version, updates the Python
dependencies, refreshes the systemd service and restarts SmartGrill.
Configuration stored in `.env`, `config.json` and the local `data/` directory
is retained.

## Important notes

- Web Push notifications require SmartGrill to be served over HTTPS. On iOS
  and iPadOS, install SmartGrill on the Home Screen before enabling
  notifications.
- Set `VAPID_SUBJECT` to a public HTTPS URL or a real contact email address.
  Local hostnames and `.local` email domains are rejected by Apple Web Push.
- The settings and push endpoints do not provide application-level
  authentication. Protect internet-facing installations through an
  authenticated reverse proxy and do not expose port 8000 directly.
- Probe mapping has been verified with the ToGrill AT-02. Compatible
  thermometers may expose their sensors in a different order.

Thank you to everyone testing SmartGrill on real hardware and helping bring
the project to its first stable release.
