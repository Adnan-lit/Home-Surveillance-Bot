#!/usr/bin/env python3
"""
Capture face images into tools/dataset/<name>/ for training.

Example:
  python3 tools/capture_images.py --name Adnan --count 60
"""

import argparse
import os
import time
from datetime import datetime

import cv2
from picamera2 import Picamera2


def ensure_dir(p: str) -> None:
    os.makedirs(p, exist_ok=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True, help="Person name (folder name)")
    ap.add_argument("--count", type=int, default=50, help="How many photos")
    ap.add_argument("--out", default="tools/dataset", help="Dataset root")
    ap.add_argument("--size", default="640x480", help="WxH, e.g. 640x480")
    args = ap.parse_args()

    w, h = [int(x) for x in args.size.lower().split("x")]
    out_dir = os.path.join(args.out, args.name)
    ensure_dir(out_dir)

    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": "BGR888", "size": (w, h)}))
    picam2.start()
    time.sleep(1.5)

    print("[INFO] Press 'c' to capture, 'q' to quit. Auto-capture starts in 2 seconds…")
    time.sleep(2)

    captured = 0
    while captured < args.count:
        frame = picam2.capture_array()
        cv2.putText(frame, f"{args.name}  {captured}/{args.count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.imshow("Capture", frame)
        key = cv2.waitKey(1) & 0xFF

        # auto-capture every ~0.25s if you don't press keys
        if key == ord("q"):
            break
        if key == ord("c") or key == 255:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = os.path.join(out_dir, f"{args.name}_{ts}.jpg")
            cv2.imwrite(path, frame)
            captured += 1
            print("[OK]", path)
            time.sleep(0.25)

    cv2.destroyAllWindows()
    picam2.stop()
    print("[DONE] captured:", captured)


if __name__ == "__main__":
    main()
