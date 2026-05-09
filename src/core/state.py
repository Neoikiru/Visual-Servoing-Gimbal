import threading
from typing import Optional, Tuple

import numpy as np


class SystemState:
    """Thread-safe shared memory for the tracking pipeline."""

    def __init__(self):
        self._lock = threading.Lock()
        self.is_running = True

        # Camera Data
        self._current_frame: Optional[np.ndarray] = None
        self._frame_capture_time: float = 0.0

        # AI Data
        self._raw_x: Optional[float] = None
        self._raw_y: Optional[float] = None
        self._gesture: str = "Searching..."

        # Parameters for tuning
        self.horizon: float = 0.15  # Predict ahead amount
        self.q_accel: float = 50000.0  # Process Noise (Acceleration)
        self.r_noise: float = 100.0  # Measurement Noise

    # Frame Methods
    def set_frame(self, frame: np.ndarray, capture_time: float):
        with self._lock:
            self._current_frame = frame.copy()
            self._frame_capture_time = capture_time

    def get_frame(self) -> Tuple(Optional[np.ndarray], float):
        with self._lock:
            return (
                self._current_frame.copy() if self._current_frame is not None else None
            ), self._frame_capture_time

    # AI Methods
    def set_detection(self, x: Optional[float], y: Optional[float], gesture: str):
        with self._lock:
            self._raw_x = x
            self._raw_y = y
            self._gesture = gesture

    def get_detection(self) -> Tuple[Optional[float], Optional[float], str]:
        with self._lock:
            return self._raw_x, self._raw_y, self._gesture

    # Tuning
    def update_tuning(self, horizon: float, q_accel: float, r_noise: float):
        with self._lock:
            self.horizon = horizon
            self.q_accel = q_accel
            self.r_noise = r_noise

    def get_tuning(self) -> Tuple[float, float, float]:
        with self._lock:
            return self.horizon, self.q_accel, self.r_noise

    # System Control
    def stop(self):
        with self._lock:
            self.is_running = False

    def check_running(self) -> bool:
        with self._lock:
            return self.is_running
