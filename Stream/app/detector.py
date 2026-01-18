import os
import time
import pickle
from datetime import datetime

import cv2
import numpy as np
import face_recognition

from .telegram_utils import send_telegram_alert

def load_encodings(path="encodings.pickle"):
    print("[INFO] loading encodings...")
    with open(path, "rb") as f:
        data = pickle.loads(f.read())
    known_face_encodings = data["encodings"]
    known_face_names = data["names"]
    if not known_face_encodings or not known_face_names:
        raise RuntimeError("encodings.pickle is empty or invalid. Re-train encodings first.")
    return known_face_encodings, known_face_names


class UnknownDetector:
    def __init__(self,
                 known_face_encodings,
                 known_face_names,
                 unknown_dir="unknown_faces",
                 unknown_cooldown=10,
                 compare_tolerance=0.45,
                 distance_max_for_known=0.55,
                 cv_scaler=4):
        self.known_face_encodings = known_face_encodings
        self.known_face_names = known_face_names

        self.UNKNOWN_SAVE_DIR = unknown_dir
        os.makedirs(self.UNKNOWN_SAVE_DIR, exist_ok=True)

        self.UNKNOWN_COOLDOWN = unknown_cooldown
        self.last_unknown_time = 0.0

        self.COMPARE_TOLERANCE = compare_tolerance
        self.DISTANCE_MAX_FOR_KNOWN = distance_max_for_known

        self.cv_scaler = int(cv_scaler)

        # same variables as your old code :contentReference[oaicite:4]{index=4}
        self.face_locations = []
        self.face_encodings = []
        self.face_names = []
        self.alert_unknown_index = -1

    def process_frame(self, frame):
        # same idea as your old process_frame :contentReference[oaicite:5]{index=5}
        self.alert_unknown_index = -1

        resized_frame = cv2.resize(frame, (0, 0), fx=1 / self.cv_scaler, fy=1 / self.cv_scaler)
        rgb_resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)

        self.face_locations = face_recognition.face_locations(rgb_resized_frame)
        self.face_encodings = face_recognition.face_encodings(
            rgb_resized_frame, self.face_locations, model="large"
        )

        self.face_names = []

        for i, face_encoding in enumerate(self.face_encodings):
            matches = face_recognition.compare_faces(
                self.known_face_encodings, face_encoding, tolerance=self.COMPARE_TOLERANCE
            )

            name = "Unknown"
            face_distances = face_recognition.face_distance(self.known_face_encodings, face_encoding)
            best_match_index = int(np.argmin(face_distances))
            best_distance = float(face_distances[best_match_index])

            if matches[best_match_index] and best_distance < self.DISTANCE_MAX_FOR_KNOWN:
                name = self.known_face_names[best_match_index]
            else:
                now = time.time()
                if now - self.last_unknown_time > self.UNKNOWN_COOLDOWN:
                    self.last_unknown_time = now
                    self.alert_unknown_index = i
                    print("[ALERT] Unknown person detected! (face index:", i, ")")

            self.face_names.append(name)

        return frame

    def handle_unknown_and_send(self, frame):
        # same idea as your old draw_results alert block :contentReference[oaicite:6]{index=6}
        for i, ((top, right, bottom, left), name) in enumerate(zip(self.face_locations, self.face_names)):
            # scale back up to original frame
            top *= self.cv_scaler
            right *= self.cv_scaler
            bottom *= self.cv_scaler
            left *= self.cv_scaler

            if i == self.alert_unknown_index and name == "Unknown":
                face_img = frame[top:bottom, left:right]
                if face_img.size != 0:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filepath = os.path.join(self.UNKNOWN_SAVE_DIR, f"unknown_{timestamp}.jpg")
                    cv2.imwrite(filepath, face_img)

                    alert_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    message = f"🚨 ALERT: Unknown person detected!\n🕒 Time: {alert_time}"
                    send_telegram_alert(message, filepath)

                self.alert_unknown_index = -1  # send once

    def step(self, picam2):
        # IMPORTANT: capture from main, like your old scripts (stable)
        frame = picam2.capture_array("main")
        self.process_frame(frame)
        self.handle_unknown_and_send(frame)


def run_detection_loop(picam2, detector: UnknownDetector, sleep_s=0.001):
    while True:
        try:
            detector.step(picam2)
            time.sleep(sleep_s)
        except Exception as e:
            print("Detection loop error:", e)
            time.sleep(1)
