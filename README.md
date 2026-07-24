# SmartGrill

SmartGrill is a lightweight web dashboard and REST API for the ToGrill AT-02 Bluetooth BBQ thermometer. It is designed to run on a Raspberry Pi and automatically reconnect to the thermometer when the Bluetooth connection is interrupted.

## Features

- Live web dashboard for ambient and probe temperatures
- Support for Probe 1 through Probe 4
- Automatic Bluetooth reconnect
- REST API for integrations such as Homey
- Health endpoint for monitoring
- Automatic startup through systemd
- Suitable for use behind a reverse proxy
- Tested on Raspberry Pi Zero W

## Requirements

- Raspberry Pi with Bluetooth support
- Raspberry Pi OS
- Python 3
- ToGrill AT-02 or compatible thermometer
- Network connection for the dashboard and API

## Installation

Clone the repository:

```bash
git clone https://github.com/Noctowl17/smartgrill.git
cd smartgrill
```

Create the local configuration:

```bash
cp .env.example .env
nano .env
```

Set the Bluetooth MAC address of the thermometer:

```dotenv
TOGRILL_ADDRESS=AA:BB:CC:DD:EE:FF
```

Run the installer:

```bash
sudo bash install.sh
```

The installer creates a Python virtual environment, installs the dependencies, installs the systemd service, and starts SmartGrill.

> On slower Raspberry Pi models, compiling `dbus-fast` during the first installation can take a considerable amount of time. As long as compiler processes are using CPU, the installation is still progressing.

## Configuration

Open `http://IP-ADDRESS:8000/settings` to configure:

- the thermometer's Bluetooth MAC address;
- reconnect and stale-data intervals;
- the display names for the ambient sensor and four external probes.

Web-managed settings are stored locally in `config.json`. This file is ignored by Git.

The `.env` file supplies the initial defaults and the web server settings:

| Variable | Default | Description |
|---|---:|---|
| `TOGRILL_ADDRESS` | `AA:BB:CC:DD:EE:FF` | Bluetooth MAC address of the thermometer |
| `SMARTGRILL_HOST` | `0.0.0.0` | Address on which the web server listens |
| `SMARTGRILL_PORT` | `8000` | TCP port for the dashboard and API |
| `RECONNECT_DELAY` | `10` | Seconds before reconnecting after a Bluetooth error |
| `STALE_AFTER` | `15` | Seconds after which temperature data is considered stale |

After changing `.env`, restart SmartGrill:

```bash
sudo systemctl restart smartgrill
```

## Web interface and API

Replace `IP-ADDRESS` with the IP address or hostname of the Raspberry Pi.

- Dashboard: `http://IP-ADDRESS:8000/`
- Settings: `http://IP-ADDRESS:8000/settings`
- Status API: `http://IP-ADDRESS:8000/api/status`
- Settings API: `http://IP-ADDRESS:8000/api/settings`
- Health API: `http://IP-ADDRESS:8000/api/health`
- OpenAPI documentation: `http://IP-ADDRESS:8000/docs`

### Status example

```json
{
  "device": "AT-02",
  "connected": true,
  "battery": 86,
  "last_update": "2026-07-23T22:10:00+02:00",
  "temperatures": {
    "kamado": 112.4,
    "probe_1": 67.8,
    "probe_2": null,
    "probe_3": null,
    "probe_4": null
  }
}
```

## Probe mapping

For the tested AT-02 model, the received temperature list is mapped as follows:

- index 0: Probe 1
- index 1: Probe 2
- index 2: Probe 3
- index 3: Probe 4
- index 6: ambient / kamado

Compatible devices may expose a different mapping.

## Service management

Check the service status:

```bash
sudo systemctl status smartgrill
```

View live logs:

```bash
journalctl -u smartgrill -f
```

Restart the service:

```bash
sudo systemctl restart smartgrill
```

SmartGrill is enabled automatically and starts when the Raspberry Pi boots.

## Updating

From the repository directory:

```bash
./update.sh
```

The update script pulls the latest changes, updates Python dependencies, reinstalls the systemd service definition, and restarts SmartGrill.

## Troubleshooting

### The service does not start

```bash
sudo systemctl status smartgrill
journalctl -u smartgrill -n 100 --no-pager
```

### The thermometer is not found

- Verify that the thermometer is powered on.
- Verify the MAC address in `.env`.
- Make sure another phone or computer is not already connected to the thermometer.
- Move the Raspberry Pi closer to the thermometer.

### Installation appears stuck on `dbus-fast`

On ARMv6 devices such as the Raspberry Pi Zero W, this package may need to be compiled locally. Check activity in a second SSH session:

```bash
ps -eo pid,etime,%cpu,%mem,cmd | grep -E 'pip|gcc|cc1|python' | grep -v grep
```

If `gcc` or `cc1` is using CPU, compilation is still running.

## Roadmap

Planned improvements include:

- Target temperatures and alerts
- Temperature graphs and history
- MQTT support
- Improved Homey integration
- Bluetooth device scanning and a first-run setup wizard

## Contributing

Issues and pull requests are welcome. Please test changes on a separate branch before merging them into `main`.

## License

This project is licensed under the terms in [LICENSE](LICENSE).
