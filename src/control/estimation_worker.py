import time

import cv2
import numpy as np
from PySide6.QtCore import QThread, Signal

from src.core.state import SystemState
from src.estimation.kalman import KalmanFilter2D
from src.utils.logger import logger


class EstimationWorker(QThread):
    # Signals for UI
    frame_ready = Signal(np.ndarray)
    telemetry_ready = Signal(dict)

    def __init__(self, state: SystemState):
        super().__init__()
        self.state = state
        self.kalman = KalmanFilter2D(dt=0.016)
        self.last_time = time.time()

    def run(self):
        logger.info("Estimation Thread Started.")

        while self.state.check_running():
            # Fetch latest data
            frame = self.state.get_frame()
            if frame is None:
                time.sleep(0.01)
                continue

            raw_x, raw_y, gesture = self.state.get_detection()

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
                    (20, 120),
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

            # Draw Predicted Future, 100ms ahead
            horizon = 0.10
            future_x = int(filt_x + (vel_x * horizon) + (0.5 * acc_x * (horizon**2)))
            future_y = int(filt_y + (vel_y * horizon) + (0.5 * acc_y * (horizon**2)))

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

            # Update for UI
            telemetry_data = {
                "raw_x": float(raw_x) if raw_x is not None else filt_x,
                "filt_x": filt_x,
                "future_x": float(future_x),
            }

            self.frame_ready.emit(frame)
            self.telemetry_ready.emit(telemetry_data)

            # ~60 FPS
            time.sleep(0.016)

        logger.info("Estimation Thread Stopped.")
