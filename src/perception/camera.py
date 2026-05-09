import json
import logging
from pathlib import Path
from typing import Tuple

import cv2
import numpy as np

logger = logging.getLogger("Tracker")


class Camera:
    def __init__(
        self,
        source: Union[int, str],  # noqa: F821
        calib_file: str = "data/calibration/camera_intrinsics.json",
    ):
        self.cap = cv2.VideoCapture(source, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(source)
            if not self.cap.isOpened():
                logger.critical(f"Could not open camera {source}")
                raise RuntimeError(f"Could not open camera {source}")

        # Force MJPG and 1280x720 @ 30 FPS
        self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)

        # Verify
        w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        logger.info(f"Initialized {w}x{h} on {source}")

        self.mtx = None
        self.dist = None
        self._load_calibration(calib_file)

    def _load_calibration(self, calib_file: str) -> None:
        """Loads the intrinsic matrix and distortion coefficients."""
        calib_path = Path(calib_file)
        if calib_path.exists():
            with open(calib_path, "r") as f:
                data = json.load(f)
                self.mtx = np.array(data["camera_matrix"])
                self.dist = np.array(data["dist_coeff"])
            logger.info(f"Loaded calibration from {calib_file}")
        else:
            logger.warn(f"Calibration not found at {calib_file}.")

    def read(self) -> Tuple[bool, np.ndarray]:
        """Reads a frame and undistorts it."""
        ret, frame = self.cap.read()
        if not ret:
            return False, frame

        # Apply the flattening if calib file loaded successfully
        if self.mtx is not None and self.dist is not None:
            frame = cv2.undistort(frame, self.mtx, self.dist, None, self.mtx)

        return True, frame

    def release(self) -> None:
        self.cap.release()
