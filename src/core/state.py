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

        # AI Data
        self._raw_x: Optional[float] = None
        self._raw_y: Optional[float] = None
        self._gesture: str = "Searching..."

    # Frame Methods
    def set_frame(self, frame: np.ndarray):
        with self._lock:
            self._current_frame = frame.copy()

    def get_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return (
                self._current_frame.copy() if self._current_frame is not None else None
            )

    # AI Methods
    def set_detection(self, x: Optional[float], y: Optional[float], gesture: str):
        with self._lock:
            self._raw_x = x
            self._raw_y = y
            self._gesture = gesture

    def get_detection(self) -> Tuple[Optional[float], Optional[float], str]:
        with self._lock:
            return self._raw_x, self._raw_y, self._gesture

    # System Control
    def stop(self):
        with self._lock:
            self.is_running = False

    def check_running(self) -> bool:
        with self._lock:
            return self.is_running
