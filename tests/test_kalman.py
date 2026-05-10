"""Tests for the KalmanFilter2D class."""

import numpy as np

from src.estimation.kalman import KalmanFilter2D


def test_kalman_initialization():
    """Verifies that the first coordinate injection inits the state properly."""
    kf = KalmanFilter2D()
    assert not kf.initialized

    accepted = kf.update((500.0, 300.0))

    assert accepted
    assert kf.initialized
    assert kf.x[0, 0] == 500.0
    assert kf.x[1, 0] == 300.0


def test_kalman_constant_velocity_prediction():
    """Injects a known velocity and proves the filter predicts frames accurately."""
    kf = KalmanFilter2D()
    kf.update((0.0, 0.0))  # Initialize at origin

    # Override internal state to force X axis velocity of 10 px/sec
    kf.x[2, 0] = 10.0  # vel_x
    kf.x[3, 0] = 0.0  # vel_y

    # Predict 1 second forward
    kf.predict(dt=1.0)

    # New position should be old pos (0) + vel (10) * dt (1) = 10.0
    assert np.isclose(kf.x[0, 0], 10.0)


# @generated [all] Gemini 3.1 Pro:
#   Prompt: Generate mahalanobis test for following implementation.
def test_mahalanobis_glitch_rejection():
    """Proves that extreme coordinates are ignored."""
    kf = KalmanFilter2D()
    kf.update((500.0, 500.0))

    # Tighten covariance to make the filter highly confident
    kf.P = np.eye(6, dtype=np.float32) * 1.0

    # Inject a severe, single-frame jump to (5000, 5000)
    accepted = kf.update((5000.0, 5000.0))

    # Filter should reject this measurement completely to prevent wild tracking spikes
    assert not accepted
    assert kf.x[0, 0] == 500.0  # State must remain uncorrupted
