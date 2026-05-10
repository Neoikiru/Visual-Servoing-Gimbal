import threading
from typing import Optional, Tuple

import numpy as np

from src.utils.config import ConfigManager


class SystemState:
    """Thread-safe shared memory for the tracking pipeline."""

    def __init__(self):
        self._lock = threading.Lock()
        # Main
        self.request_reset: bool = False
        self._tracking_enabled: bool = False
        self.is_running = True
        self._is_paused = False

        # Config manager
        self.config_mgr = ConfigManager()
        cfg = self.config_mgr.config

        # Data Buffers
        self._current_frame: Optional[np.ndarray] = None
        self._frame_capture_time: float = 0.0
        self._raw_x: Optional[float] = None
        self._raw_y: Optional[float] = None
        self._gesture: str = "Searching..."

        # Parameters for tuning
        self.horizon: float = cfg["kalman"]["horizon"]  # Predict ahead amount
        self.q_accel: float = cfg["kalman"]["q_accel"]  # Process Noise (Acceleration)
        self.r_noise: float = cfg["kalman"]["r_noise"]  # Measurement Noise

        # PID (PD)
        self.kp_x: float = cfg["pid"]["kp_x"]
        self.kd_x: float = cfg["pid"]["kd_x"]
        self.kp_y: float = cfg["pid"]["kp_y"]
        self.kd_y: float = cfg["pid"]["kd_y"]

        # Hardware
        self.steps_per_pixel_x: float = cfg["hardware"]["steps_per_pixel_x"]
        self.steps_per_pixel_y: float = cfg["hardware"]["steps_per_pixel_y"]
        self.pixels_per_step_x: float = cfg["hardware"]["pixels_per_step_x"]
        self.pixels_per_step_y: float = cfg["hardware"]["pixels_per_step_y"]

    def get_hardware_ratios(self) -> Tuple[float, float]:
        with self._lock:
            return self.steps_per_pixel_x, self.steps_per_pixel_y

    def get_feedforward_ratios(self):
        with self._lock:
            return self.pixels_per_step_x, self.pixels_per_step_y

    def update_pid(self, kp_x: float, kd_x: float, kp_y: float, kd_y: float):
        with self._lock:
            self.kp_x, self.kd_x = kp_x, kd_x
            self.kp_y, self.kd_y = kp_y, kd_y

    def get_pid(self) -> tuple[float, float, float, float]:
        with self._lock:
            return self.kp_x, self.kd_x, self.kp_y, self.kd_y

    def set_paused(self, paused: bool):
        with self._lock:
            self._is_paused = paused

    def is_paused(self) -> bool:
        with self._lock:
            return self._is_paused

    def set_tracking(self, enabled: bool):
        with self._lock:
            self._tracking_enabled = enabled

    def is_tracking_enabled(self) -> bool:
        with self._lock:
            return self._tracking_enabled

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

    def save_config(self):
        """Syncs active variables to JSON and saves to disk."""
        with self._lock:
            cfg = self.config_mgr.config
            cfg["kalman"]["horizon"] = self.horizon
            cfg["kalman"]["q_accel"] = self.q_accel
            cfg["kalman"]["r_noise"] = self.r_noise
            cfg["pid"]["kp_x"] = self.kp_x
            cfg["pid"]["kd_x"] = self.kd_x
            cfg["pid"]["kp_y"] = self.kp_y
            cfg["pid"]["kd_y"] = self.kd_y
            cfg["hardware"]["steps_per_pixel_x"] = self.steps_per_pixel_x
            cfg["hardware"]["steps_per_pixel_y"] = self.steps_per_pixel_y
            self.config_mgr.save()

    def stop(self):
        with self._lock:
            self.is_running = False

    def check_running(self) -> bool:
        with self._lock:
            return self.is_running
