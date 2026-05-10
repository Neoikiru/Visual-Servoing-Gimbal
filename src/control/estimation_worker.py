import logging
import math
import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from src.control.pid import PDController
from src.control.serial_link import SerialLink
from src.core.state import SystemState
from src.estimation.kalman import KalmanFilter2D

logger = logging.getLogger("Tracker")


class EstimationWorker(QThread):
    # Signals for UI
    frame_ready = Signal(np.ndarray)
    telemetry_ready = Signal(dict)

    def __init__(self, state: SystemState, args):
        super().__init__()
        self.state = state

        # Initialize Kalman
        self.kalman = KalmanFilter2D()
        self.last_time = time.time()

        # Initialize PID
        kp_x, kd_x, kp_y, kd_y = state.get_pid()
        self.pd_x = PDController(kp=kp_x, kd=kd_x)
        self.pd_y = PDController(kp=kp_y, kd=kd_y)

        self.steps_per_pixel_x, self.steps_per_pixel_y = state.get_hardware_ratios()

        # Initialize Serial Comms
        self.serial = SerialLink(
            port=args.port, baudrate=args.baud, debug_mode=args.debug
        )
        self.serial.connect()

    def run(self):
        logger.info("Estimation Thread Started.")

        while self.state.check_running():
            if self.state.is_paused():
                self.last_time = time.time()
                time.sleep(0.05)
                continue

            # Rewind request
            if self.state.request_reset:
                logger.info("Wiping Kalman Filter state for new test run.")
                self.kalman.x = np.zeros((6, 1), dtype=np.float32)
                self.kalman.P = np.eye(6, dtype=np.float32) * 500.0
                self.kalman.initialized = False
                self.state.request_reset = False

            # Fetch latest data
            frame, capture_time = self.state.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            raw_x, raw_y, gesture = self.state.get_detection()
            if time.time() % 1.0 < 0.01:
                logger.debug(f"raw_x: {raw_x}, raw_y: {raw_y}, gesture: {gesture}")

            # Tuning Parameters
            horizon, q_accel, r_noise = self.state.get_tuning()
            self.kalman.R = np.eye(2, dtype=np.float32) * r_noise
            self.kalman.Q[4:6, 4:6] = np.eye(2, dtype=np.float32) * q_accel

            # Kalman update (mandatory)
            current_time = time.time()
            dt = current_time - self.last_time
            self.last_time = current_time

            self.kalman.predict(dt)

            # Kalman update
            if raw_x is not None and raw_y is not None:
                cv2.drawMarker(
                    frame, (raw_x, raw_y), (255, 0, 0), cv2.MARKER_CROSS, 20, 2
                )
                accepted = self.kalman.update((float(raw_x), float(raw_y)))
                if not accepted:
                    cv2.putText(
                        frame,
                        "Glitch Ignored",
                        (20, 120),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.7,
                        (0, 165, 255),
                        2,
                    )
            else:
                cv2.putText(
                    frame,
                    "Target Lost",
                    (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    (0, 255, 255),
                    2,
                )

            # Extract states
            filt_x, filt_y = float(self.kalman.x[0, 0]), float(self.kalman.x[1, 0])
            vel_x, vel_y = float(self.kalman.x[2, 0]), float(self.kalman.x[3, 0])
            acc_x, acc_y = float(self.kalman.x[4, 0]), float(self.kalman.x[5, 0])

            # Draw Filtered Present
            cv2.circle(frame, (int(filt_x), int(filt_y)), 10, (0, 255, 255), -1)

            # Draw Predicted Future\
            future_x = int(filt_x + (vel_x * horizon) + (0.5 * acc_x * (horizon**2)))
            future_y = int(filt_y + (vel_y * horizon) + (0.5 * acc_y * (horizon**2)))

            # update PID
            kp_x, kd_x, kp_y, kd_y = self.state.get_pid()
            self.pd_x.update_gains(kp_x, kd_x)
            self.pd_y.update_gains(kp_y, kd_y)

            # Get screen center to target
            h, w = frame.shape[:2]
            center_x, center_y = w / 2.0, h / 2.0

            # Crosshair in the center
            cv2.drawMarker(
                frame,
                (int(center_x), int(center_y)),
                (0, 255, 0),
                cv2.MARKER_CROSS,
                40,
                1,
            )

            # Get error
            err_x = future_x - center_x
            err_y = future_y - center_y

            # Get PID output
            pd_out_x = self.pd_x.compute(err_x, current_time)
            pd_out_y = self.pd_y.compute(err_y, current_time)

            # Convert pixels to steps
            steps_x = int(pd_out_x * self.steps_per_pixel_x)
            steps_y = int(-pd_out_y * self.steps_per_pixel_y)

            # Send to hardware
            if self.state.is_tracking_enabled():
                self.serial.send_target(steps_x, steps_y)

            box_size = 40
            cv2.rectangle(
                frame,
                (future_x - box_size, future_y - box_size),
                (future_x + box_size, future_y + box_size),
                (0, 0, 255),
                2,
            )

            cv2.putText(
                frame,
                f"Gesture: {gesture}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )

            # Calculate metrics
            latency_ms = (time.time() - capture_time) * 1000
            spatial_err = 0.0
            if raw_x is not None and raw_y is not None:
                spatial_err = math.sqrt(
                    (future_x - raw_x) ** 2 + (future_y - raw_y) ** 2
                )

            # Update for UI
            telemetry_data = {
                "raw_x": float(raw_x) if raw_x is not None else filt_x,
                "filt_x": filt_x,
                "future_x": float(future_x),
                "raw_y": float(raw_y) if raw_y is not None else filt_x,
                "filt_y": filt_y,
                "future_y": float(future_y),
                "latency": latency_ms,
                "error": spatial_err,
            }

            self.frame_ready.emit(frame)
            self.telemetry_ready.emit(telemetry_data)

            # ~60 FPS
            time.sleep(0.016)

        logger.info("Estimation Thread Stopped.")

    def quit(self):
        """Ensure we close the serial port on shutdown."""
        self.serial.close()
        super().quit()
