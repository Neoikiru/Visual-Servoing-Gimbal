"""
Tool: Gesture Inference Test
Loads the ONNX model and MediaPipe to classify gestures live from the webcam.
"""

# pylint: disable=duplicate-code
import json
from pathlib import Path
from typing import Dict

import cv2
import mediapipe as mp
import numpy as np
import onnxruntime as ort
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# From second script
HAND_CONNECTIONS = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),  # Thumb
    (0, 5),
    (5, 6),
    (6, 7),
    (7, 8),  # Index
    (5, 9),
    (9, 10),
    (10, 11),
    (11, 12),  # Middle
    (9, 13),
    (13, 14),
    (14, 15),
    (15, 16),  # Ring
    (13, 17),
    (0, 17),
    (17, 18),
    (18, 19),
    (19, 20),  # Pinky & Palm base
]


# @generated [partially] Gemini 3.1 Pro: ONNX model usage.
# pylint: disable=too-many-locals,too-many-statements,duplicate-code
def test_live_inference(camera_id: int = 0) -> None:
    """
    Runs live inference using the trained ONNX model and MediaPipe.

    :param camera_id: The OpenCV camera index.
    """
    # pylint: disable=duplicate-code
    # paths
    models_dir = Path("data/models")
    onnx_path = models_dir / "gesture_classifier.onnx"
    mapping_path = models_dir / "label_mapping.json"
    mp_task_path = models_dir / "hand_landmarker.task"

    if not onnx_path.exists() or not mapping_path.exists():
        raise FileNotFoundError("Model files missing.")

    # Label Mapping
    with open(mapping_path, "r", encoding="utf-8") as f:
        # convert JSON keys back to integers
        label_mapping: Dict[int, str] = {int(k): v for k, v in json.load(f).items()}

    # Initialize ONNX Runtime Session
    print("Loading ONNX Execution Provider...")
    ort_session = ort.InferenceSession(str(onnx_path))
    input_name = ort_session.get_inputs()[0].name

    # Init MediaPipe API
    print("Loading MediaPipe...")
    base_options = python.BaseOptions(model_asset_path=str(mp_task_path))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    detector = vision.HandLandmarker.create_from_options(options)

    # Start Camera
    cap = cv2.VideoCapture(camera_id, cv2.CAP_V4L2)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera {camera_id}.")

    print(
        "Frame default resolution: ("
        + str(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        + "; "
        + str(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        + ")"
    )

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))

    # Request the higher resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    # Request 30 FPS
    cap.set(cv2.CAP_PROP_FPS, 30)

    # verify it worked
    actual_w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    actual_h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    print(f"Initialized at resolution: {actual_w} x {actual_h}")

    print("Live inference started. Press 'q' to quit.")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        # Convert to RGB for MediaPipe
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Detect hands
        detection_result = detector.detect(mp_image)

        current_gesture = "Searching..."
        box_color = (0, 0, 255)

        if detection_result.hand_landmarks:
            hand_landmarks = detection_result.hand_landmarks[0]
            h, w, _ = frame.shape

            # Extract and normalize coordinates
            raw_coords = [[lm.x, lm.y, lm.z] for lm in hand_landmarks]
            wrist_x, wrist_y, wrist_z = raw_coords[0]

            normalized_features = []
            for x, y, z in raw_coords:
                normalized_features.extend(
                    [
                        round(x - wrist_x, 6),
                        round(y - wrist_y, 6),
                        round(z - wrist_z, 6),
                    ]
                )

            # Prepare for ONNX (must be [1, 63], type float32)
            input_data = np.array([normalized_features], dtype=np.float32)

            # Run Inference
            ort_outputs = ort_session.run(None, {input_name: input_data})
            # ONNX returns a list of outputs. The first one is the predicted integer ID.
            predicted_id = int(ort_outputs[0][0])

            # Map ID to String
            current_gesture = label_mapping.get(predicted_id, "Unknown")

            # Draw Skeleton
            for lm in hand_landmarks:
                cx, cy = int(lm.x * w), int(lm.y * h)
                cv2.circle(frame, (cx, cy), 5, (255, 0, 0), cv2.FILLED)
            for connection in HAND_CONNECTIONS:
                p1 = hand_landmarks[connection[0]]
                p2 = hand_landmarks[connection[1]]
                cv2.line(
                    frame,
                    (int(p1.x * w), int(p1.y * h)),
                    (int(p2.x * w), int(p2.y * h)),
                    (0, 255, 0),
                    2,
                )

            # Change UI color if Open gesture is detected
            if current_gesture == "Open":
                box_color = (0, 255, 0)

        # UI
        cv2.rectangle(frame, (0, 0), (350, 60), (0, 0, 0), -1)
        cv2.putText(
            frame,
            f"Gesture: {current_gesture}",
            (10, 40),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.2,
            box_color,
            3,
        )

        cv2.imshow("ONNX Real-Time Inference Test", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    test_live_inference(camera_id=4)
