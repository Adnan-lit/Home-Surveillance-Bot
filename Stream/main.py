import threading
from app.camera_stream import create_camera
from app.detector import load_encodings, UnknownDetector, run_detection_loop
from app.webapp import create_app

def main():
    known_enc, known_names = load_encodings("encodings.pickle")

    picam2, output = create_camera(main_size=(1920, 1080), lores_size=(640, 360), fps=15)

    detector = UnknownDetector(
        known_enc, known_names,
        unknown_dir="unknown_faces",
        unknown_cooldown=10,
        compare_tolerance=0.45,
        distance_max_for_known=0.55,
        cv_scaler=4
    )

    threading.Thread(target=run_detection_loop, args=(picam2, detector), daemon=True).start()

    app = create_app(output)
    app.run(host="0.0.0.0", port=8000, threaded=True, use_reloader=False)

if __name__ == "__main__":
    main()
