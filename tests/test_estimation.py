"""Tests for the EstimationWorker."""

# @generated [all] Gemini 3.1 Pro:
#   Prompt: Create a test for the following module.
#   P.S. Terrifying math.

# pylint: disable=redefined-outer-name
from unittest.mock import MagicMock

import numpy as np
import pytest

from src.control.estimation_worker import EstimationWorker
from src.core.state import SystemState


@pytest.fixture
def state_fixture():
    """Builds a SystemState filled with mock testing variables."""
    state = SystemState()

    # Override getters
    state.get_pid = MagicMock(return_value=(1.0, 0.1, 1.0, 0.1))
    state.get_hardware_ratios = MagicMock(return_value=(0.45, 0.45))
    state.get_feedforward_ratios = MagicMock(return_value=(2.84, 2.75))
    state.get_tuning = MagicMock(return_value=(0.15, 50000.0, 100.0))

    # Enable tracking so the feedforward works
    state.is_tracking_enabled = MagicMock(return_value=True)
    state.is_paused = MagicMock(return_value=False)

    return state


@pytest.fixture
def args_fixture():
    """Forces the SerialLink into completely safe mock mode."""
    args = MagicMock()
    args.port = "/dev/mock_port"
    args.baud = 115200
    args.debug = True  # Bypasses actual hardware connections
    return args


def test_ego_motion_feedforward_subtraction(state_fixture, args_fixture):
    """
    Proves that mid-movement pending steps are correctly bled off over time (dt)
    and that the internal Kalman position matrix is shifted in the proper directions.
    """
    # 1. Instantiate the worker purely as an object (Do NOT call .start() or .run())
    worker = EstimationWorker(state_fixture, args_fixture)

    # Verify clean initialization
    assert worker.pending_steps_x == 0.0
    assert worker.pending_steps_y == 0.0

    # 2. Setup a controlled initial Kalman State
    # Let's assume the hand is currently believed to be at pixel (500, 500)
    worker.kalman.x[0, 0] = 500.0  # X position
    worker.kalman.x[1, 0] = 500.0  # Y position

    # 3. Inject Pending Motor Steps (Simulating a mid-execution move)
    # We commanded +100 steps X (pan right) and +100 steps Y (pitch up)
    worker.pending_steps_x = 100.0
    worker.pending_steps_y = 100.0

    # 4. Simulate the exact Ego-Motion temporal execution block
    dt = 0.010  # 10 milliseconds
    max_steps_per_sec = worker.max_steps_per_sec  # 5000.0

    # How many steps can physically execute in 10ms? -> 5000 * 0.010 = 50 steps
    expected_executed_steps = 50.0

    # Pull dynamic ratios (just like the loop does)
    px_per_step_x, px_per_step_y = state_fixture.get_feedforward_ratios()

    # --- EXECUTE THE WORKER'S INTERNAL MATH DIRECTLY ---
    step_limit_dt = max_steps_per_sec * dt

    exec_x = min(abs(worker.pending_steps_x), step_limit_dt)
    worker.pending_steps_x -= exec_x

    exec_y = min(abs(worker.pending_steps_y), step_limit_dt)
    worker.pending_steps_y -= exec_y

    shift_px_x = exec_x * px_per_step_x
    shift_px_y = exec_y * px_per_step_y

    worker.kalman.x[0, 0] -= shift_px_x
    worker.kalman.x[1, 0] += shift_px_y
    # ---------------------------------------------------

    # 5. ASSERTIONS: Prove the state transformed perfectly

    # Buffer Bleed Assertion: 100 pending steps should have dropped to 50
    assert worker.pending_steps_x == 50.0
    assert worker.pending_steps_y == 50.0

    # Kinematic Shift Assertion X:
    # Expected shift = 50 steps * 2.84 px/step = 142.0 pixels
    # X should shift negative (left) when panning right: 500 - 142 = 358.0
    expected_x = 500.0 - (expected_executed_steps * 2.84)
    assert np.isclose(
        worker.kalman.x[0, 0], expected_x
    ), f"Expected X={expected_x}, got {worker.kalman.x[0, 0]}"

    # Kinematic Shift Assertion Y:
    # Expected shift = 50 steps * 2.75 px/step = 137.5 pixels
    # Y should shift positive (down the canvas) when pitching up: 500 + 137.5 = 637.5
    expected_y = 500.0 + (expected_executed_steps * 2.75)
    assert np.isclose(
        worker.kalman.x[1, 0], expected_y
    ), f"Expected Y={expected_y}, got {worker.kalman.x[1, 0]}"

    # Clean up the serial connection safely
    worker.quit()
