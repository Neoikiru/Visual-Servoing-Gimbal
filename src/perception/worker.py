import json
import time
from pathlib import Path
from typing import Dict

import cv2
import mediapipe as mp
import numpy as np
import onnxruntime as ort
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from PySide6.QtCore import QObject, Signal

from src.perception.camera import Camera
from src.utils.logger import Logger


# @generated [partially] Gemini 3.1 Pro: QtApplication Structure and signals.
class TrackingWorker(QObject):
    frame_ready = Signal(np.ndarray)

    def __init__(self, camera_id: int = 4):
        super().__init__()
        self.camera_id = camera_id
        self.running = True

        # Initialize Camera module
        self.camera = Camera(camera_id=self.camera_id)

        # Initialize AI models
        self._setup_ai()

    def _setup_ai(self):
        """Loads MediaPipe Tasks API and the ONNX Classifier."""
        models_dir = Path("data/models")

        # Load Label Mapping
        with open(models_dir / "label_mapping.json", "r") as f:
            self.label_mapping: Dict[int, str] = {
                int(k): v for k, v in json.load(f).items()
            }

        # Load ONNX Runtime
        self.ort_session = ort.InferenceSession(
            str(models_dir / "gesture_classifier.onnx")
        )
        self.onnx_input_name = self.ort_session.get_inputs()[0].name

        # Load MediaPipe
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

    def run(self):
        """The main perception and estimation loop"""
        Logger.info("Tracking Thread Started.")

        while self.running:
            ret, frame = self.camera.read()
            if not ret:
                time.sleep(0.01)
                continue

            h, w, _ = frame.shape

            # PERCEPTION
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection = self.detector.detect(mp_image)

            gesture = "Searching..."

            if detection.hand_landmarks:
                landmarks = detection.hand_landmarks[0]

                # track the center of the hand
                x_coords = [lm.x for lm in landmarks]
                y_coords = [lm.y for lm in landmarks]
                raw_x = int(np.mean(x_coords) * w)
                raw_y = int(np.mean(y_coords) * h)

                # CLASSIFICATION
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

                # Blue Crosshair for rwa data
                cv2.drawMarker(
                    frame, (raw_x, raw_y), (255, 0, 0), cv2.MARKER_CROSS, 20, 2
                )

            # UI
            cv2.putText(
                frame,
                f"Gesture: {gesture}",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )

            self.frame_ready.emit(frame)

    def stop(self):
        self.running = False
        self.camera.release()
