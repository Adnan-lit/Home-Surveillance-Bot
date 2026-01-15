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
import requests


# =========================
# Telegram settings (ENV)
# =========================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_telegram_alert(message, image_path=None):
    try:
        # Send message
        msg_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        r1 = requests.post(
            msg_url,
            data={"chat_id": CHAT_ID, "text": message},
            timeout=10
        )
        print("TG message:", r1.status_code, r1.text)

        # Send photo if provided
        if image_path:
            photo_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
            with open(image_path, "rb") as photo:
                r2 = requests.post(
                    photo_url,
                    data={"chat_id": CHAT_ID},
                    files={"photo": photo},
                    timeout=20
                )
                print("TG photo:", r2.status_code, r2.text)

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

# =========================
# Unknown detection settings
# =========================
UNKNOWN_SAVE_DIR = "unknown_faces"
UNKNOWN_COOLDOWN = 10  # seconds (increase if you get too many alerts)
last_unknown_time = 0

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
cv_scaler = 4  # scale down factor

face_locations = []
face_encodings = []
face_names = []

frame_count = 0
start_time = time.time()
fps = 0

# A flag so we don't send telegram multiple times in same frame
send_unknown_now = False

# =========================
# Face processing
# =========================
def process_frame(frame):
    global face_locations, face_encodings, face_names, last_unknown_time, send_unknown_now

    send_unknown_now = False  # reset for this frame

    resized_frame = cv2.resize(frame, (0, 0), fx=1 / cv_scaler, fy=1 / cv_scaler)
    rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

    face_locations = face_recognition.face_locations(rgb_resized_frame)
    face_encodings = face_recognition.face_encodings(rgb_resized_frame, face_locations, model="large")

    face_names = []

    for face_encoding in face_encodings:
        matches = face_recognition.compare_faces(known_face_encodings, face_encoding, tolerance=0.45)
        name = "Unknown"

        face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)
        best_match_index = int(np.argmin(face_distances))

        if matches[best_match_index]:
            name = known_face_names[best_match_index]
        else:
            current_time = time.time()
            if current_time - last_unknown_time > UNKNOWN_COOLDOWN:
                last_unknown_time = current_time
                send_unknown_now = True
                print("[ALERT] Unknown person detected!")

        face_names.append(name)

    return frame

# =========================
# Draw results + save unknown + telegram
# =========================
def draw_results(frame):
    global send_unknown_now

    for (top, right, bottom, left), name in zip(face_locations, face_names):
        top *= cv_scaler
        right *= cv_scaler
        bottom *= cv_scaler
        left *= cv_scaler

        color = (0, 0, 255) if name == "Unknown" else (0, 255, 0)

        cv2.rectangle(frame, (left, top), (right, bottom), color, 3)
        cv2.rectangle(frame, (left, top - 35), (right, top), color, cv2.FILLED)
        cv2.putText(frame, name, (left + 6, top - 6),
                    cv2.FONT_HERSHEY_DUPLEX, 1.0, (255, 255, 255), 1)

        # Save + send telegram only if cooldown triggered (send_unknown_now=True)
        if name == "Unknown" and send_unknown_now:
            face_img = frame[top:bottom, left:right]
            if face_img.size != 0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = f"{UNKNOWN_SAVE_DIR}/unknown_{timestamp}.jpg"
                cv2.imwrite(filepath, face_img)

                send_telegram_alert("🚨 ALERT: Unknown person detected!", filepath)

            # after sending once, stop sending again this frame
            send_unknown_now = False

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
while True:
    frame = picam2.capture_array()

    processed_frame = process_frame(frame)
    display_frame = draw_results(processed_frame)

    current_fps = calculate_fps()
    cv2.putText(display_frame, f"FPS: {current_fps:.1f}",
                (display_frame.shape[1] - 150, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Video", display_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
picam2.stop()
