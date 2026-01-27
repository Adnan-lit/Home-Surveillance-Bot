#!/usr/bin/env python3
"""
Surveillance Bot - Final (Raspberry Pi)

Features
- Picamera2 MJPEG live stream (Flask) with Basic Auth
- Face recognition: alert + save unknown face images + Telegram notification
- Robot control (Arduino over Serial) from the web dashboard
- Optional safety: STOP robot when unknown detected

Run:
  python3 main.py
Then open:
  http://<pi-ip>:8000  (username/password from config/dashboard_config.py)
"""

import os
import threading
import time

from bot_app.camera_stream import create_camera
from bot_app.detector import load_encodings, UnknownDetector, run_detection_loop
from bot_app.webapp import create_app

from bot_app.robot_serial import RobotSerial, SerialConfig
from bot_app.telegram_utils import send_telegram_alert
from config.bot_config import (
    SERIAL_PORT,
    SERIAL_BAUD,
    STOP_ON_UNKNOWN,
    SENSOR_ALERTS_ENABLED,
    SENSOR_ALERT_COOLDOWN_S,
    STOP_ON_FLAME,
    STOP_ON_GAS,
)


def main():
    # --- Robot Serial ---
    robot = RobotSerial(SerialConfig(port=SERIAL_PORT, baud=SERIAL_BAUD))

    # --- Sensor alert handlers (Flame + MQ-2) ---
    last_flame_alert = 0.0
    last_gas_alert = 0.0

    def on_sensor(state):
        nonlocal last_flame_alert, last_gas_alert
        if not SENSOR_ALERTS_ENABLED:
            return

        now = time.time()

        # Flame
        if state.flame and (now - last_flame_alert) > float(SENSOR_ALERT_COOLDOWN_S):
            last_flame_alert = now
            msg = f"🔥 FIRE ALERT! Flame detected\nFlame value: {state.flame_val}\nMQ2: {state.mq2_val}"
            send_telegram_alert(msg)
            if STOP_ON_FLAME:
                robot.stop()

        # Gas / Smoke (ignore during warm-up)
        if (not state.warm) and state.gas and (now - last_gas_alert) > float(SENSOR_ALERT_COOLDOWN_S):
            last_gas_alert = now
            msg = f"⚠️ GAS/SMOKE ALERT! (MQ-2)\nMQ2 value: {state.mq2_val}\nFlame: {state.flame_val}"
            send_telegram_alert(msg)
            if STOP_ON_GAS:
                robot.stop()

    # Start background serial reader (for SENSOR lines)
    robot.start_reader(on_sensor=on_sensor)

    # --- Face encodings ---
    enc_path = os.path.join(os.path.dirname(__file__), "encodings.pickle")
    known_enc, known_names = load_encodings(enc_path)

    # --- Camera ---
    picam2, output = create_camera(main_size=(1920, 1080), lores_size=(640, 360), fps=15)

    # --- Unknown callback ---
    def on_unknown(_img_path: str):
        if STOP_ON_UNKNOWN:
            robot.stop()

    detector = UnknownDetector(
        known_enc, known_names,
        unknown_dir=os.path.join(os.path.dirname(__file__), "unknown_faces"),
        unknown_cooldown=10,
        compare_tolerance=0.45,
        distance_max_for_known=0.55,
        cv_scaler=4,
        on_unknown=on_unknown
    )

    # Run face detection loop in background
    threading.Thread(target=run_detection_loop, args=(picam2, detector), daemon=True).start()

    # Web app (stream + robot control)
    app = create_app(output, robot=robot)
    app.run(host="0.0.0.0", port=8000, threaded=True, use_reloader=False)


if __name__ == "__main__":
    main()
