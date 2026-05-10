"""
Worker thread for camera frame grabbing and distribution.
"""

import logging
import time
from typing import Optional

import cv2
from PySide6.QtCore import QThread, Signal  # pylint: disable=no-name-in-module

from src.core.state import SystemState
from src.perception.camera import Camera

logger = logging.getLogger("Tracker")


class CameraWorker(QThread):  # pylint: disable=too-few-public-methods
    """
    Thread responsible for reading frames from a camera or video file
    and updating the shared SystemState.
    """

    video_finished = Signal()

    def __init__(
        self,
        state: SystemState,
        camera_id: int = 4,
        video_path: Optional[str] = None,
    ):
        super().__init__()
        self.state = state
        self.camera_id = camera_id
        self.video_path = video_path
        self.rewind_requested = False

    def run(self):
        """Main execution loop for frame grabbing."""
        if self.video_path:
            logger.info(
                "Camera Thread Started in [VIDEO MODE] playing: %s", self.video_path
            )
            source = self.video_path
        else:
            logger.info(
                "Camera Thread Started in [LIVE MODE] on Camera ID: %s", self.camera_id
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
