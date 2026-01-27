# Surveillance Bot (Raspberry Pi + Arduino)

This project merges:
- **Live camera dashboard** (Flask + MJPEG)
- **Face recognition** (known vs unknown)
- **Telegram alerts** with unknown face image
- **Robot control** (Arduino over Serial) + **AUTO Line Follower mode**

## Folder overview
- `main.py` : run this on Raspberry Pi
- `bot_app/` : camera stream, detection, web UI, serial control
- `config/` : dashboard login + telegram + serial settings
- `unknown_faces/` : saved unknown face crops
- `tools/` : capture photos + train encodings
- `arduino/` : Arduino Mega/Uno code (Adafruit Motor Shield v1)

## 1) Setup (Raspberry Pi)
```bash
cd surveillance_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Edit configs:
- `config/dashboard_config.py`
- `config/telegram_config.py`
- `config/bot_config.py` (serial port)

## 2) Train face encodings
1) Capture images:
```bash
source venv/bin/activate
python3 tools/capture_images.py --name Adnan --count 60
```

2) Train encodings:
```bash
python3 tools/train_encodings.py --dataset tools/dataset --out encodings.pickle
```

## 3) Run
```bash
source venv/bin/activate
python3 main.py
```
Open: `http://<PI_IP>:8000`

## Arduino notes
- Upload `arduino/mega_motor_shield_linefollower_serial.ino`
- Commands supported:
  `STOP, AUTO_LF, MANUAL, FWD, BACK, LEFT, RIGHT, SPEED <0-255>`

## Flame + MQ-2 Sensors (optional)
The Arduino sketch also supports **Flame (analog)** and **MQ-2 (analog)** monitoring.

### Wiring (recommended)
- Line follower IR sensors: `A0` (left), `A1` (right)
- Flame sensor analog output: `A2`
- MQ-2 analog output: `A3`

### Dashboard + Telegram
When the Arduino sends `SENSOR ...` lines, the dashboard shows live sensor status.
Telegram alerts are enabled/disabled in `config/bot_config.py`:
- `SENSOR_ALERTS_ENABLED`
- `SENSOR_ALERT_COOLDOWN_S`
- Optional: `STOP_ON_FLAME`, `STOP_ON_GAS`

## Power (important)
- Power **Arduino/Mega by USB** (from Pi) is OK for logic only.
- Motors must use a **separate motor battery pack** connected to the Motor Shield power input.
- **Share GND** between motor battery and Arduino/Motor Shield.
