from picamera2 import Picamera2
import cv2
import face_recognition
import pickle

# Load known face encodings
with open("../encodings/family_faces.pkl", "rb") as f:
    known_encodings, known_names = pickle.load(f)

picam2 = Picamera2()
picam2.configure(
    picam2.create_preview_configuration(
        main={"format": "BGR888", "size": (640, 480)}
    )
)
picam2.start()

while True:
    frame = picam2.capture_array()
    rgb = frame[:, :, ::-1]  # BGR → RGB

    # Detect faces internally (NO face_locations passed)
    face_encodings = face_recognition.face_encodings(rgb)

    # Get face locations separately (for drawing only)
    face_locations = face_recognition.face_locations(rgb)

    for (top, right, bottom, left), face_encoding in zip(
        face_locations, face_encodings
    ):
        matches = face_recognition.compare_faces(
            known_encodings, face_encoding, tolerance=0.5
        )

        name = "Unknown"
        if True in matches:
            name = known_names[matches.index(True)]

        cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
        cv2.putText(
            frame,
            name,
            (left, top - 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2,
        )

    cv2.imshow("Face Recognition", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cv2.destroyAllWindows()
picam2.stop()
