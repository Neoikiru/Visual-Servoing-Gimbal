"""
Tool: Camera Intrinsic Calibration
Captures a checkerboard pattern to calculate the camera matrix
    and distortion coefficients.
Reference documentation: https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

import cv2
import numpy as np


def calibrate_camera(
    board_size: Tuple[int, int] = (9, 6),
    frame_wait: float = 1.0,
    required_frames: int = 20,
    camera_id: int = 0,
) -> None:
    """
    Runs the live camera feed to collect checkerboard corners and calculates intrinsics.

    :param board_size: Number of inner corners on the checkerboard (width, height).
    :param frame_wait: Time in seconds to wait between capturing frames.
    :param required_frames: How many valid captures are needed before calculating.
    :param camera_id: The OpenCV webcam ID.
    """
    print(
        f"Starting calibration. "
        f"Place a {board_size} checkerboard in front of the camera."
    )

    # termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

    # prepare object points, like (0,0,0), (1,0,0), (2,0,0) ....,(6,5,0)
    obj_p = np.zeros((board_size[0] * board_size[1], 3), np.float32)
    obj_p[:, :2] = np.mgrid[0 : board_size[0], 0 : board_size[1]].T.reshape(
        -1, 2
    )  # pylint: disable=no-member

    # Arrays to store object points and image points from all the images.
    obj_points: List[np.ndarray] = []  # 3d point in real world space.
    img_points: List[np.ndarray] = []  # 2d points in image plane.

    cap = cv2.VideoCapture(camera_id, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open camera {camera_id}.")

    # Force MJPG and 1280x720 @ 30 FPS
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cap.set(cv2.CAP_PROP_FPS, 30)

    frames_captured = 0
    last_capture_time = time.time()
    gray_shape = None

    while frames_captured < required_frames:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_shape = gray.shape[::-1]

        # Find the chess board corners
        ret_corners, corners = cv2.findChessboardCorners(gray, board_size, None)

        # If found, add object points, image points (after refining them)
        if ret_corners:
            corners_refined = cv2.cornerSubPix(
                gray, corners, (11, 11), (-1, -1), criteria
            )

            # Draw and display the corners
            cv2.drawChessboardCorners(frame, board_size, corners_refined, ret_corners)

            # Capture only if enough time has passed (ensure different positions)
            if time.time() - last_capture_time > frame_wait:
                obj_points.append(obj_p)
                img_points.append(corners_refined)
                frames_captured += 1
                last_capture_time = time.time()
                print(f"Captured {frames_captured}/{required_frames} frames...")

        # Display info
        cv2.putText(
            frame,
            f"Captures: {frames_captured}/{required_frames}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            (0, 255, 0),
            2,
        )
        cv2.imshow("Calibration (Press 'q' to abort)", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            print("Calibration aborted by user.")
            cap.release()
            cv2.destroyAllWindows()
            return

    cap.release()
    cv2.destroyAllWindows()

    if frames_captured < required_frames:
        print("Not enough frames captured.")
        return

    print("Calculating camera matrix... Please wait.")
    _, mtx, dist, _, _ = cv2.calibrateCamera(
        obj_points, img_points, gray_shape, None, None
    )

    save_calibration(mtx, dist)


def save_calibration(mtx: np.ndarray, dist: np.ndarray) -> None:
    """Saves the calculated matrices to a JSON file."""
    output_dir = Path("data/calibration")
    output_dir.mkdir(parents=True, exist_ok=True)

    calib_data: Dict[str, Any] = {
        "camera_matrix": mtx.tolist(),
        "dist_coeff": dist.tolist(),
    }

    out_file = output_dir / "camera_intrinsics.json"
    with open(out_file, "w") as f:
        json.dump(calib_data, f, indent=4)

    print(f"Calibration done! Data saved to {out_file}")


if __name__ == "__main__":
    calibrate_camera(board_size=(9, 7), required_frames=20, camera_id=4)
