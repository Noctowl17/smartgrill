# SmartGrill

WiFi-dashboard en REST API voor een ToGrill AT-02 via een Raspberry Pi met Bluetooth.

## Functies

- Kamado/ambient en Probe 1 t/m 4
- Live dashboard op poort 8000
- REST API voor Homey
- Automatisch opnieuw verbinden
- Automatisch starten via systemd
- Geschikt voor een reverse proxy

## Installatie op Raspberry Pi OS

```bash
git clone https://github.com/JOUW-GEBRUIKERSNAAM/smartgrill.git
cd smartgrill
sudo ./install.sh
```

Het standaard Bluetooth-adres is al ingesteld op:

```text
AA:BB:CC:DD:EE:FF
```

Aanpassen kan in `.env`.

## URLs

- Dashboard: `http://IP-VAN-DE-PI:8000/`
- Status-API: `http://IP-VAN-DE-PI:8000/api/status`
- Health-API: `http://IP-VAN-DE-PI:8000/api/health`
- OpenAPI: `http://IP-VAN-DE-PI:8000/docs`

## Homey API-voorbeeld

`GET /api/status`:

```json
{
  "device": "AT-02",
  "connected": true,
  "battery": 13,
  "last_update": "2026-07-23T22:10:00+02:00",
  "temperatures": {
    "kamado": null,
    "probe_1": 31.4,
    "probe_2": null,
    "probe_3": null,
    "probe_4": null
  }
}
```

## Beheer

```bash
sudo systemctl status smartgrill
journalctl -u smartgrill -f
sudo systemctl restart smartgrill
```

Bijwerken:

```bash
cd ~/smartgrill
./update.sh
```

## Probe-mapping AT-02

Voor dit model is de ontvangen lijst als volgt gemapt:

- index 0: Probe 1
- index 1: Probe 2
- index 2: Probe 3
- index 3: Probe 4
- index 6: ambient/kamado
