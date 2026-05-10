"""Tests for the PDController class."""

import time

import pytest

from src.control.pid import PDController


def test_pid_proportional_response():
    """Verifies pure proportional output when derivative is zero."""
    pd = PDController(kp=2.0, kd=0.0)

    # 100 pixels off center
    error = 100.0
    current_time = time.time()

    output = pd.compute(error, current_time)

    # Output should strictly be Kp * error (2.0 * 100 = 200.0)
    assert output == 200.0


def test_pid_derivative_braking():
    """Verifies that closing the error rapidly applies a negative force."""
    pd = PDController(kp=1.0, kd=0.5)

    start_time = time.time()

    # Initialize previous error at 100px
    pd.compute(100.0, start_time)

    # Error drops rapidly to 50px over 0.1 seconds
    new_time = start_time + 0.1
    output = pd.compute(50.0, new_time)

    # Proportional term = 1.0 * 50.0 = 50.0
    # Derivative term = (50.0 - 100.0) / 0.1 = -500.0 * Kd (0.5) = -250.0
    # Total expected output = 50.0 - 250.0 = -200.0

    # Flot point err, so use approx
    assert output == pytest.approx(-200.0, abs=1e-2)


def test_pid_reset():
    """Ensures resetting the controller wipes internal derivative memory."""
    pd = PDController(kp=1.0, kd=1.0)
    pd.compute(100.0, time.time())

    pd.reset()
    assert pd.prev_error == 0.0
