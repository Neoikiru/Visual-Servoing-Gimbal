import logging
import time

import cv2
from PySide6.QtCore import QThread, Signal

from src.core.state import SystemState
from src.perception.camera import Camera

logger = logging.getLogger("Tracker")


class CameraWorker(QThread):
    video_finished = Signal()

    def __init__(
        self,
        state: SystemState,
        camera_id: int = 4,
        video_path: Optional[str] = None,  # noqa: F821
    ):
        super().__init__()
        self.state = state
        self.camera_id = camera_id
        self.video_path = video_path
        self.rewind_requested = False

    def run(self):
        if self.video_path:
            logger.info(
                f"Camera Thread Started in [VIDEO MODE] playing: {self.video_path}"
            )
            source = self.video_path
        else:
            logger.info(
                f"Camera Thread Started in [LIVE MODE] on Camera ID: {self.camera_id}"
            )
            source = self.camera_id

        camera = Camera(source=source)

        fps = camera.cap.get(cv2.CAP_PROP_FPS)
        if fps <= 0 or fps > 120:
            fps = 30.0
        frame_delay = 1.0 / fps

        total_frames = (
            int(camera.cap.get(cv2.CAP_PROP_FRAME_COUNT)) if self.video_path else 0
        )

        while self.state.check_running():
            start_time = time.time()
            ret, frame = camera.read()

            # For some reason ret was not actually returning when video ended, so...
            current_frame = (
                int(camera.cap.get(cv2.CAP_PROP_POS_FRAMES)) if self.video_path else 0
            )
            video_ended = self.video_path and (not ret or current_frame >= total_frames)

            if not ret and not video_ended:
                time.sleep(0.01)
                continue

            if video_ended:
                logger.info("End of video reached. Pausing.")
                self.state.set_paused(True)
                self.video_finished.emit()

                # Spinlock
                while not self.rewind_requested and self.state.check_running():
                    time.sleep(0.1)

                if not self.state.check_running():
                    break

                if self.rewind_requested:
                    camera.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    self.rewind_requested = False
                    logger.info("Video rewound. Restarting test cycle.")
                    continue

            self.state.set_frame(frame, time.time())

            if self.video_path:
                sleep_time = frame_delay - (time.time() - start_time)
                if sleep_time > 0:
                    time.sleep(sleep_time)
            else:
                time.sleep(0.005)

        camera.release()
        logger.info("Camera Thread Stopped.")
