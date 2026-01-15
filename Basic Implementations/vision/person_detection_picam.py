from picamera2 import Picamera2
import cv2
from ultralytics import YOLO
import time

# Load YOLOv8 nano (fast for Raspberry Pi)
model = YOLO("models/yolov8n.pt")

# Initialize camera
picam2 = Picamera2()
picam2.configure(
    picam2.create_preview_configuration(
        main={"format": "BGR888", "size": (640, 480)}
    )
)
picam2.start()

PERSON_CLASS_ID = 0  # COCO dataset: person
CONF_THRESHOLD = 0.6

last_detection_time = 0
DETECTION_COOLDOWN = 3  # seconds

while True:
    frame = picam2.capture_array()

    # Run YOLO inference
    results = model(frame, stream=True)

    person_detected = False

    for result in results:
        for box in result.boxes:
            cls = int(box.cls[0])
            conf = float(box.conf[0])

            if cls == PERSON_CLASS_ID and conf > CONF_THRESHOLD:
                person_detected = True

                x1, y1, x2, y2 = map(int, box.xyxy[0])

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"Person {conf:.2f}",
                    (x1, y1 - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 255, 0),
                    2,
                )

    # Event trigger
    current_time = time.time()
    if person_detected and (current_time - last_detection_time) > DETECTION_COOLDOWN:
        print("🚶 Person detected!")
        cv2.imwrite("person_detected.jpg", frame)
        last_detection_time = current_time

    cv2.imshow("YOLO Person Detection", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cv2.destroyAllWindows()
picam2.stop()
