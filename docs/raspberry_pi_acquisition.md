# Raspberry Pi Chef iQ Acquisition

This guide runs the existing Chef iQ BLE scanner and session recorder on a Raspberry Pi. It records probe measurements locally every two seconds. Heater control and Wi-Fi reporting are not part of this first capture step.

## Requirements

- Raspberry Pi 3 Model B with Raspberry Pi OS
- Bluetooth enabled and BlueZ installed
- The project files on the Pi
- Python 3.11 or newer

Bleak uses BlueZ over D-Bus on Linux. Keep the Pi's Bluetooth service running while the capture program is active.

## Install

If the project has been pushed to GitHub, clone it on the Pi:

```bash
git clone https://github.com/kurt-morehouse/Weber-smoker-with-LNN-control.git
cd Weber-smoker-with-LNN-control
```

Install the OS packages and enable Bluetooth:

```bash
sudo apt update
sudo apt install -y bluez python3-venv
sudo systemctl enable --now bluetooth
```

Create an isolated Python environment and install the acquisition dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r acquisition/requirements.txt
```

Check that BlueZ sees the adapter:

```bash
bluetoothctl show
```

The output should include a powered Bluetooth controller. If it is not powered, open `bluetoothctl`, enter `power on`, then `quit`.

## Capture

Power on the Chef iQ probes and place them near the Pi. From the project directory, run:

```bash
bash/run_pi_capture.bash
```

The program prints live readings and writes a session under `data/sessions/`. Each probe gets its own CSV file. A session manifest is written alongside the CSV files. The recorder continues to write a row on each two-second sample even when a probe's values have not changed.

Stop capture with **Ctrl+C**. The session is then marked complete.

Unknown probes are still recorded with generated names. To label them, use the Mac GUI's probe-label editor and copy the resulting `probe_labels.json` to the project root on the Pi, or edit that JSON file on the Pi.

## Troubleshooting

- **No Bluetooth adapter:** check `bluetoothctl show`, then verify Bluetooth is enabled in Raspberry Pi OS.
- **No probes discovered:** power on the probes, keep them close to the Pi, and check that the BlueZ service is active with `systemctl status bluetooth`.
- **Python dependency errors:** confirm the Pi uses Python 3.11 or newer and install requirements inside `.venv`.
- **Permission or D-Bus errors:** run the program as your normal Pi user, not with `sudo`; confirm the system Bluetooth service is active.

The current scanner reads broadcast advertisements passively; it does not connect to the Chef iQ probes or require their hub.
