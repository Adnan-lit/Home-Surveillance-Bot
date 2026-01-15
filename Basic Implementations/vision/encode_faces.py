import face_recognition
import os
import pickle

IMAGE_DIR = "../faces/person1"
ENCODING_FILE = "../encodings/family_faces.pkl"

os.makedirs("../encodings", exist_ok=True)

encodings = []
names = []

for file in os.listdir(IMAGE_DIR):
    if file.endswith(".jpg"):
        image = face_recognition.load_image_file(
            os.path.join(IMAGE_DIR, file)
        )
        face_encs = face_recognition.face_encodings(image)

        if face_encs:
            encodings.append(face_encs[0])
            names.append("person1")

with open(ENCODING_FILE, "wb") as f:
    pickle.dump((encodings, names), f)

print("Face encoding saved successfully")
