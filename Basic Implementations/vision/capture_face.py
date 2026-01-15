from picamera2 import Picamera2
import cv2
import os

SAVE_DIR = "../faces/person1"
os.makedirs(SAVE_DIR, exist_ok=True)

picam2 = Picamera2()
picam2.configure(
    picam2.create_preview_configuration(
        main={"format": "BGR888", "size": (640, 480)}
    )
)
picam2.start()

count = 0

while True:
    frame = picam2.capture_array()
    cv2.imshow("Capture Face - Press C", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord('c'):
        count += 1
        filename = f"{SAVE_DIR}/{count}.jpg"
        cv2.imwrite(filename, frame)
        print(f"Saved {filename}")

    if count >= 5 or key == ord('q'):
        break

cv2.destroyAllWindows()
picam2.stop()
