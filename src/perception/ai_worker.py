"""
Worker thread for AI hand landmark detection and gesture recognition.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict

import cv2
import mediapipe as mp
import numpy as np
import onnxruntime as ort
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PySide6.QtCore import QThread  # pylint: disable=no-name-in-module

from src.core.state import SystemState

logger = logging.getLogger("Tracker")


# @generated [partially] Gemini 3.1 Pro: Added comments, help with ONNX usage.
class AIWorker(QThread):  # pylint: disable=too-few-public-methods
    """
    Thread that uses MediaPipe and ONNX to detect hand landmarks
        and recognize gestures.
    """

    def __init__(self, state: SystemState):
        """Initializes the AI worker with shared system state."""
        super().__init__()
        self.state = state
        self.label_mapping = {}
        self.ort_session = None
        self.onnx_input_name = None
        self.detector = None
        self._setup_ai()

    def _setup_ai(self):
        """Loads MediaPipe Tasks API and the ONNX Classifier."""
        models_dir = Path("data/models")

        # Load Label Mapping
        with open(models_dir / "label_mapping.json", "r", encoding="utf-8") as f:
            self.label_mapping: Dict[int, str] = {
                int(k): v for k, v in json.load(f).items()
            }

        # Load ONNX Runtime
        self.ort_session = ort.InferenceSession(
            str(models_dir / "gesture_classifier.onnx")
        )
        self.onnx_input_name = self.ort_session.get_inputs()[0].name

        # Load MediaPipe
        # pylint: disable=duplicate-code
        base_options = python.BaseOptions(
            model_asset_path=str(models_dir / "hand_landmarker.task")
        )
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.7,
            min_hand_presence_confidence=0.7,
            min_tracking_confidence=0.7,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    # pylint: disable=too-many-locals
    def run(self):
        """Main execution loop for hand detection."""
        logger.info("AI Thread Started.")

        while self.state.check_running():
            if self.state.is_paused():
                time.sleep(0.05)
                continue

            frame, capture_time = self.state.get_frame()
            if frame is None:
                logger.debug("Frame is None.")
                time.sleep(0.01)
                continue

            h, w, _ = frame.shape

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection = self.detector.detect(mp_image)

            gesture = "Searching..."
            raw_x, raw_y = None, None

            if detection.hand_landmarks:
                landmarks = detection.hand_landmarks[0]

                # track the center of the hand
                x_coords = [lm.x for lm in landmarks]
                y_coords = [lm.y for lm in landmarks]
                raw_x = int(np.mean(x_coords) * w)
                raw_y = int(np.mean(y_coords) * h)

                raw_coords = [[lm.x, lm.y, lm.z] for lm in landmarks]
                wrist_x, wrist_y, wrist_z = raw_coords[0]

                norm_features = []
                for x, y, z in raw_coords:
                    norm_features.extend(
                        [
                            round(x - wrist_x, 6),
                            round(y - wrist_y, 6),
                            round(z - wrist_z, 6),
                        ]
                    )

                input_data = np.array([norm_features], dtype=np.float32)
                ort_outputs = self.ort_session.run(
                    None, {self.onnx_input_name: input_data}
                )
                gesture = self.label_mapping.get(int(ort_outputs[0][0]), "Unknown")

            # Push results
            self.state.set_detection(raw_x, raw_y, gesture, capture_time)

            time.sleep(0.005)

        logger.info("AI Thread Stopped.")
