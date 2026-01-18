# app/camera_stream.py
# Fast MJPEG streaming output for Flask, compatible with newer Picamera2 encoder signatures.
# One camera instance, provides:
#   - create_camera(...) -> (picam2, output)
#   - mjpeg_generator(output) -> generator yielding multipart MJPEG frames

import threading
import time
from typing import Tuple

from picamera2 import Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import Output


class StreamingOutput(Output):
    """
    Picamera2 Output that keeps the latest JPEG frame in memory.
    The MJPEGEncoder calls outputframe(...). Newer Picamera2 versions pass
    extra args (packet, audio), so we accept them.
    """
    def __init__(self) -> None:
        super().__init__()
        self.frame: bytes | None = None
        self.cond = threading.Condition()

    def outputframe(self, frame, keyframe=True, timestamp=None, packet=None, audio=None):
        # 'frame' is bytes for MJPEGEncoder
        with self.cond:
            self.frame = frame
            self.cond.notify_all()


def create_camera(
    main_size: Tuple[int, int] = (1280, 720),
    lores_size: Tuple[int, int] = (640, 360),
    fps: int = 15,
    main_format: str = "XRGB8888",
    warmup_s: float = 0.8,
):
    """
    Creates and starts Picamera2 with a main stream (for MJPEG web view)
    and a lores stream (for detection if you want).

    Returns:
        (picam2, output) where output is a StreamingOutput.
    """
    output = StreamingOutput()

    picam2 = Picamera2()
    config = picam2.create_video_configuration(
        main={"format": main_format, "size": main_size},
        lores={"size": lores_size},
        display=None
    )
    picam2.configure(config)
    picam2.start()

    # Let camera settle
    time.sleep(max(0.0, warmup_s))

    # Cap FPS to reduce CPU/thermal load
    try:
        picam2.set_controls({"FrameRate": int(fps)})
    except Exception:
        pass

    # Start MJPEG encoder on the "main" stream by default
    encoder = MJPEGEncoder()
    picam2.start_encoder(encoder, output)  # encodes main stream

    return picam2, output


def mjpeg_generator(output: StreamingOutput):
    """
    Flask streaming generator. Yields multipart MJPEG frames forever.
    """
    while True:
        with output.cond:
            output.cond.wait()
            frame = output.frame

        if frame is None:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
        )


def stop_camera(picam2: Picamera2):
    """
    Optional helper to stop encoders and camera cleanly.
    """
    try:
        picam2.stop_encoder()
    except Exception:
        pass
    try:
        picam2.stop()
    except Exception:
        pass
