"""Tests for the SystemState class in the core module."""

import numpy as np

from src.core.state import SystemState


def test_state_frame_storage():
    """Verifies that frames and capture timestamps are safely stored."""
    state = SystemState()
    dummy_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
    capture_time = 12345.67

    state.set_frame(dummy_frame, capture_time)

    retrieved_frame, retrieved_time = state.get_frame()

    assert retrieved_time == capture_time
    assert retrieved_frame is not None
    assert retrieved_frame.shape == (720, 1280, 3)

    # Ensure mem safety by verifying a clone
    assert id(retrieved_frame) != id(dummy_frame)


def test_state_tuning_updates():
    """Verifies updates to Kalman sliders."""
    state = SystemState()
    state.update_tuning(horizon=0.25, q_accel=1234.0, r_noise=56.0)

    h, q, r = state.get_tuning()

    assert h == 0.25
    assert q == 1234.0
    assert r == 56.0


def test_tracking_toggles():
    """Verifies basic state control logic."""
    state = SystemState()
    assert not state.is_tracking_enabled()

    state.set_tracking(True)
    assert state.is_tracking_enabled()
