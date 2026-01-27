#!/usr/bin/env python3
"""
Train face encodings from dataset images.

Example:
  python3 tools/train_encodings.py --dataset tools/dataset --out encodings.pickle
"""

import argparse
import os
import pickle

import cv2
import face_recognition


def list_images(root: str):
    exts = (".jpg", ".jpeg", ".png")
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.lower().endswith(exts):
                yield os.path.join(dirpath, fn)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="tools/dataset", help="Dataset root: dataset/<name>/*.jpg")
    ap.add_argument("--out", default="encodings.pickle", help="Output pickle path")
    ap.add_argument("--model", default="hog", choices=["hog", "cnn"], help="Face detector model")
    args = ap.parse_args()

    image_paths = list(list_images(args.dataset))
    if not image_paths:
        raise SystemExit(f"No images found in {args.dataset}")

    known_encodings = []
    known_names = []

    print("[INFO] processing", len(image_paths), "images…")
    for i, image_path in enumerate(image_paths, 1):
        name = os.path.basename(os.path.dirname(image_path))
        image = cv2.imread(image_path)
        if image is None:
            print("[WARN] cannot read:", image_path)
            continue

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        boxes = face_recognition.face_locations(rgb, model=args.model)
        encs = face_recognition.face_encodings(rgb, boxes)

        for e in encs:
            known_encodings.append(e)
            known_names.append(name)

        if i % 25 == 0:
            print(f"[INFO] {i}/{len(image_paths)}")

    if not known_encodings:
        raise SystemExit("No face encodings found. Try better images or change --model.")

    data = {"encodings": known_encodings, "names": known_names}
    with open(args.out, "wb") as f:
        f.write(pickle.dumps(data))
    print("[DONE] wrote:", args.out, "encodings:", len(known_encodings))


if __name__ == "__main__":
    main()
