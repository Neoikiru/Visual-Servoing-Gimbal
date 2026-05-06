"""
Tool: Gesture Data Collector
Captures hand landmarks using MediaPipe and saves normalized coordinates to CSV.
Reference documentation:
    https://ai.google.dev/edge/mediapipe/solutions/vision/hand_landmarker/python
"""

import argparse
import csv
import urllib.request
from pathlib import Path

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Hand skeleton connections for drawing
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


def download_model(model_path: Path) -> None:
    """Downloads the required MediaPipe Task model"""
    url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"  # noqa: E501
    if not model_path.exists():
        print("Downloading MediaPipe Hand Landmarker model...")
        urllib.request.urlretrieve(url, model_path)
        print("Download complete")


def collect_data(label: str, num_samples: int, camera_id: int = 0) -> None:
    # Setup Dirs
    output_dir = Path("data/datasets")
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_file = output_dir / "raw_gestures.csv"

    model_dir = Path("data/models")
    model_dir.mkdir(parents=True, exist_ok=True)
    model_path = model_dir / "hand_landmarker.task"

    download_model(model_path)

    # Prepare CSV
    write_header = not csv_file.exists()
    header = ["label"]
    for i in range(21):
        header.extend([f"x{i}", f"y{i}", f"z{i}"])

    # Init MediaPipe API
    base_options = python.BaseOptions(model_asset_path=str(model_path))
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=1,
        min_hand_detection_confidence=0.7,
        min_hand_presence_confidence=0.7,
        min_tracking_confidence=0.7,
    )
    detector = vision.HandLandmarker.create_from_options(options)

    # Open Camera
    cap = cv2.VideoCapture(camera_id)
    if not cap.isOpened():
        raise RuntimeError(f"Could not open camera {camera_id}.")

    samples_collected = 0
    print(f"Ready to collect {num_samples} samples for gesture: '{label}'.")
    print("Press 's' to start recording, 'q' to quit.")

    recording = False

    with open(csv_file, mode="a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(header)

        while samples_collected < num_samples:
            ret, frame = cap.read()
            if not ret:
                break

            # MP requires a specific mp.Image object for some reason
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = detector.detect(mp_image)

            if detection_result.hand_landmarks:
                # Track only the first hand detected
                hand_landmarks = detection_result.hand_landmarks[0]
                h, w, _ = frame.shape

                # Skeleton Drawing
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

                if recording:
                    # Extract coordinates
                    raw_coords = [[lm.x, lm.y, lm.z] for lm in hand_landmarks]

                    # Normalize relative to the wrist
                    wrist_x, wrist_y, wrist_z = raw_coords[0]
                    normalized_row = [label]

                    for x, y, z in raw_coords:
                        normalized_row.extend(
                            [
                                round(x - wrist_x, 6),
                                round(y - wrist_y, 6),
                                round(z - wrist_z, 6),
                            ]
                        )

                    writer.writerow(normalized_row)
                    samples_collected += 1

            # UI text
            status_color = (0, 0, 255) if recording else (0, 255, 0)
            status_text = (
                f"Recording: {samples_collected}/{num_samples}"
                if recording
                else "Waiting (Press 's')"
            )

            cv2.putText(
                frame,
                f"Gesture: {label}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                (255, 255, 255),
                2,
            )
            cv2.putText(
                frame,
                status_text,
                (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX,
                1,
                status_color,
                2,
            )

            cv2.imshow("Data Collector", frame)

            key = cv2.waitKey(1) & 0xFF
            if key == ord("s") and not recording:
                recording = True
                print("Recording started...")
            elif key == ord("q"):
                print("Aborted by user.")
                break

    cap.release()
    cv2.destroyAllWindows()
    print(
        f"\nSuccessfully saved {samples_collected} samples for '{label}' to {csv_file}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect hand gesture landmarks.")
    parser.add_argument(
        "--label",
        type=str,
        required=True,
        help="Name of the gesture (e.g., Open, Closed, Pinch, ...)",
    )
    parser.add_argument(
        "--samples", type=int, default=500, help="Number of frames to record"
    )
    parser.add_argument("--camera", type=int, default=0, help="Camera ID")

    args = parser.parse_args()
    collect_data(label=args.label, num_samples=args.samples, camera_id=args.camera)
