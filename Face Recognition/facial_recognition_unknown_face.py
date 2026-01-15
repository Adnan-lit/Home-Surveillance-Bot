import face_recognition
import cv2
import numpy as np
from picamera2 import Picamera2
import time
import pickle
import os
from datetime import datetime
import requests

from telegram_config import BOT_TOKEN, CHAT_ID


# =========================
# Telegram
# =========================
def send_telegram_alert(message, image_path=None):
    try:
        msg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r1 = requests.post(msg_url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
        print("TG message:", r1.status_code)

        if image_path:
            photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(image_path, "rb") as photo:
                r2 = requests.post(
                    photo_url,
                    data={"chat_id": CHAT_ID},
                    files={"photo": photo},
                    timeout=20
                )
            print("TG photo:", r2.status_code)

    except Exception as e:
        print("[ERROR] Telegram failed:", e)


# =========================
# Load face encodings
# =========================
print("[INFO] loading encodings...")
with open("encodings.pickle", "rb") as f:
    data = pickle.loads(f.read())

known_face_encodings = data["encodings"]
known_face_names = data["names"]

if not known_face_encodings or not known_face_names:
    raise RuntimeError("encodings.pickle is empty or invalid. Re-train encodings first.")


# =========================
# Unknown detection settings
# =========================
UNKNOWN_SAVE_DIR = "unknown_faces"
UNKNOWN_COOLDOWN = 10  # seconds
last_unknown_time = 0

COMPARE_TOLERANCE = 0.45
DISTANCE_MAX_FOR_KNOWN = 0.55

os.makedirs(UNKNOWN_SAVE_DIR, exist_ok=True)


# =========================
# Camera setup
# =========================
picam2 = Picamera2()
picam2.configure(
    picam2.create_preview_configuration(
        main={"format": "XRGB8888", "size": (1920, 1080)}
    )
)
picam2.start()


# =========================
# Performance settings
# =========================
cv_scaler = 4

face_locations = []
face_encodings = []
face_names = []

frame_count = 0
start_time = time.time()
fps = 0

# ✅ Instead of boolean, store WHICH face triggered the alert
alert_unknown_index = -1


# =========================
# Face processing
# =========================
def process_frame(frame):
    global face_locations, face_encodings, face_names, last_unknown_time, alert_unknown_index

    alert_unknown_index = -1  # reset each frame

    resized_frame = cv2.resize(frame, (0, 0), fx=1 / cv_scaler, fy=1 / cv_scaler)
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(
        rgb_resized_frame, face_locations, model="large"
    )

    face_names = []

    for i, face_encoding in enumerate(face_encodings):
        matches = face_recognition.compare_faces(
            known_face_encodings, face_encoding, tolerance=COMPARE_TOLERANCE
        )

        name = "Unknown"

        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = int(np.argmin(face_distances))
        best_distance = float(face_distances[best_match_index])

        if matches[best_match_index] and best_distance < DISTANCE_MAX_FOR_KNOWN:
            name = known_face_names[best_match_index]
        else:
            current_time = time.time()
            if current_time - last_unknown_time > UNKNOWN_COOLDOWN:
                last_unknown_time = current_time
                alert_unknown_index = i  # ✅ remember exactly which face
                print("[ALERT] Unknown person detected! (face index:", i, ")")

        face_names.append(name)

    return frame


# =========================
# Draw results + save unknown + telegram
# =========================
def draw_results(frame):
    global alert_unknown_index

    for i, ((top, right, bottom, left), name) in enumerate(zip(face_locations, face_names)):
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler

        color = (0, 0, 255) if name == "Unknown" else (0, 255, 0)

        cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
        cv2.rectangle(frame, (left - 3, top - 35), (right + 3, top), color, cv2.FILLED)
        cv2.putText(
            frame, name, (left + 6, top - 6),
            cv2.FONT_HERSHEY_DUPLEX, 1.0,
            (255, 255, 255), 1
        )

        # ✅ Send alert ONLY for the face that triggered the cooldown
        if i == alert_unknown_index and name == "Unknown":
            face_img = frame[top:bottom, left:right]
            if face_img.size != 0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"{UNKNOWN_SAVE_DIR}/unknown_{timestamp}.jpg"
                cv2.imwrite(filepath, face_img)

                alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                message = f"🚨 ALERT: Unknown person detected!\n🕒 Time: {alert_time}"
                send_telegram_alert(message, filepath)

            alert_unknown_index = -1  # ✅ sent once

    return frame


# =========================
# FPS calculation
# =========================
def calculate_fps():
    global frame_count, start_time, fps
    frame_count += 1
    elapsed_time = time.time() - start_time
    if elapsed_time >= 1:
        fps = frame_count / elapsed_time
        frame_count = 0
        start_time = time.time()
    return fps


# =========================
# Main loop
# =========================
try:
    while True:
        frame = picam2.capture_array()

        processed_frame = process_frame(frame)
        display_frame = draw_results(processed_frame)

        current_fps = calculate_fps()
        cv2.putText(
            display_frame, f"FPS: {current_fps:.1f}",
            (display_frame.shape[1] - 150, 30),
            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2
        )

        cv2.imshow("Video", display_frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

finally:
    cv2.destroyAllWindows()
    picam2.stop()
