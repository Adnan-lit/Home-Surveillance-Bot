# config/bot_config.py
# Serial settings for Arduino connection
SERIAL_PORT = "/dev/ttyACM0"   # or /dev/ttyUSB0
SERIAL_BAUD = 9600

# If True, when an unknown face is detected, the robot will send STOP
STOP_ON_UNKNOWN = True

# =========================
# Environmental Sensors (Flame + MQ-2)
# =========================
# Arduino periodically sends: SENSOR FLAME=0/1 GAS=0/1 MQ2VAL=xxx FLAMEVAL=xxx WARM=0/1
# These settings control alerting on the Raspberry Pi.
SENSOR_ALERTS_ENABLED = True

# Telegram spam control
SENSOR_ALERT_COOLDOWN_S = 20

# Optional safety: stop motors on hazard detection
STOP_ON_FLAME = False
STOP_ON_GAS = False
