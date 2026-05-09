"""
2D Second-Order Kalman Filter.
Based on the following:
    "Kalman and Bayesian Filters in Python"
        by Roger R Labbe Jr (May 23, 2020), Chapter 8.3.3.
    "filterpy.kalman.KalmanFilter" source code by Roger R Labbe Jr
Link to the repo:
    https://github.com/rlabbe/Kalman-and-Bayesian-Filters-in-Python
"""

import logging
from typing import Tuple

import numpy as np

logger = logging.getLogger("Tracker")


# @generated [partially] Gemini 3.1 Pro: Suggested using mahalanobis distance
#   to filter out the outliers and a lot of help with debugging...
class KalmanFilter2D:
    def __init__(self, dt: float = 0.016):
        # State: [x, y, vx, vy, ax, ay]
        self.x = np.zeros((6, 1), dtype=np.float32)

        # Measurement Matrix
        self.H = np.array(
            [
                # x  y vx vy ax ay
                [1, 0, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0],
            ],
            dtype=np.float32,
        )

        # Covariance Matrix P (Uncertainty)
        self.P = np.eye(6, dtype=np.float32)
        self.P[0:2, 0:2] *= 10.0  # Position
        self.P[2:4, 2:4] *= 100.0  # Velocity
        self.P[4:6, 4:6] *= 1000.0  # Acceleration

        # Measurement Noise R (Trust in camera)
        self.R = np.eye(2, dtype=np.float32) * 100.0

        # Process Noise Q (Trust in physics)
        self.Q = np.eye(6, dtype=np.float32)
        self.Q[0:2, 0:2] *= 10.0  # Position
        self.Q[2:4, 2:4] *= 1000.0  # Velocity
        self.Q[4:6, 4:6] *= 50000.0  # Acceleration

        # State Transition F
        self.F = np.eye(6, dtype=np.float32)

        # Identity matrix
        self._I = np.eye(6, dtype=np.float32)

        self.initialized = False
        self.consecutive_gates = 0
        self.max_coast_frames = 15

    def _update_F(self, dt: float) -> None:
        """Kinematics for Constant Acceleration."""
        dt2 = 0.5 * (dt**2)
        self.F[0, 2], self.F[1, 3] = dt, dt  # Position += Velocity * dt
        self.F[0, 4], self.F[1, 5] = dt2, dt2  # Position += 0.5 * Accel * dt^2
        self.F[2, 4], self.F[3, 5] = dt, dt  # Velocity += Accel * dt

    def predict(self, dt: float) -> Tuple[float, float]:
        """prediction step (Adapted from FilterPy)."""
        self._update_F(dt)

        # x = Fx
        self.x = np.dot(self.F, self.x)

        # P = FPF' + Q
        self.P = np.dot(np.dot(self.F, self.P), self.F.T) + self.Q

        return float(self.x[0, 0]), float(self.x[1, 0])

    def update(self, measurement: Tuple[float, float]) -> bool:
        """Add a new measurement to the Kalman filter."""
        z = np.array([[measurement[0]], [measurement[1]]], dtype=np.float32)

        # Initialization
        if not self.initialized:
            self.x[0, 0] = z[0, 0]
            self.x[1, 0] = z[1, 0]
            self.initialized = True
            logger.info(f"Kalman Filter Initialized at ({z[0, 0]:.0f}, {z[1, 0]:.0f})")
            return True

        # y = z - Hx
        # error (residual) between measurement and prediction
        y = z - np.dot(self.H, self.x)

        # common subexpression for speed
        PHT = np.dot(self.P, self.H.T)

        S = np.dot(self.H, PHT) + self.R
        S_inv = np.linalg.inv(S)

        # Calculate distances
        pixel_dist = np.linalg.norm(y)

        # Mahalanobis distance of measurement.
        # How many standard deviations away P (Data point)
        #   is from the mean of D (probability distribution)
        mahalanobis_sq = np.dot(np.dot(y.T, S_inv), y)[0, 0]

        dynamic_gate_limit = 25.0  # mahalanobis distance threshold
        absolute_pixel_limit = 100.0  # mix jerk in pixels to trigger

        # Outlier rejection
        if mahalanobis_sq > dynamic_gate_limit and pixel_dist > absolute_pixel_limit:
            self.consecutive_gates += 1
            logger.debug(
                f"Gated: Mahal {mahalanobis_sq:.1f}, "
                f"Dist {pixel_dist:.1f}px (Streak: {self.consecutive_gates})"
            )

            # LOSS OF TRACK RESET
            if self.consecutive_gates >= self.max_coast_frames:
                logger.debug("Target lost. Hard resetting filter to new position.")
                self.x = np.zeros((6, 1), dtype=np.float32)
                self.x[0, 0] = z[0, 0]
                self.x[1, 0] = z[1, 0]
                self.consecutive_gates = 0
                return True

            return False  # Ignore the glitch

        self.consecutive_gates = 0

        # Update

        # map system uncertainty into kalman gain
        K = np.dot(PHT, S_inv)

        # x = x + Ky
        # predict new x with residual scaled by the kalman gain
        self.x = self.x + np.dot(K, y)

        I_KH = self._I - np.dot(K, self.H)
        self.P = np.dot(np.dot(I_KH, self.P), I_KH.T) + np.dot(np.dot(K, self.R), K.T)

        return True
