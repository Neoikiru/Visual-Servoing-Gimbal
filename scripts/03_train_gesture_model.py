"""
Tool: Gesture Model Trainer
Trains a Random Forest classifier on the collected landmark data and exports to ONNX.
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder


def load_dataset(csv_path: Path) -> Tuple[np.ndarray, np.ndarray, List[str]]:
    """Reads the CSV dataset and splits it into features and labels."""
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path}.")

    X: List[List[float]] = []
    y_raw: List[str] = []

    with open(csv_path, "r") as f:
        reader = csv.reader(f)
        header = next(reader)  # Skip header

        for row in reader:
            if not row:
                continue
            y_raw.append(row[0])
            # The rest are 63 float coordinates
            X.append([float(val) for val in row[1:]])

    return np.array(X, dtype=np.float32), np.array(y_raw), header[1:]


# @generated [partially] Gemini 3.1 Pro: Suggestion on using ONXN & conversion to ONNX.
def train_and_export() -> None:
    # paths
    dataset_path = Path("data/datasets/raw_gestures.csv")
    models_dir = Path("data/models")
    models_dir.mkdir(parents=True, exist_ok=True)

    onnx_path = models_dir / "gesture_classifier.onnx"
    mapping_path = models_dir / "label_mapping.json"

    # Load Data
    print("Loading dataset...")
    X, y_raw, _ = load_dataset(dataset_path)
    print(f"Loaded {len(X)} samples with {X.shape[1]} features each.")

    # Encode String Labels to int
    le = LabelEncoder()
    y = le.fit_transform(y_raw)

    # Save the mapping for future use
    label_mapping: Dict[int, str] = {
        int(index): label for index, label in enumerate(le.classes_)
    }
    with open(mapping_path, "w") as f:
        json.dump(label_mapping, f, indent=4)
    print(f"Label mapping saved: {label_mapping}")

    # Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Train the Model
    print("\nTraining Random Forest Classifier...")
    clf = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    clf.fit(X_train, y_train)

    # Evaluate the Model
    y_pred = clf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy on Test Data: {acc * 100:.2f}%\n")
    print(classification_report(y_test, y_pred, target_names=le.classes_))

    # Convert to ONNX
    print("\nConverting model to ONNX format...")
    # input shape is 1 sample at a time, 63 features wide
    initial_type = [("float_input", FloatTensorType([None, X.shape[1]]))]

    onnx_model = convert_sklearn(clf, initial_types=initial_type, target_opset=12)

    # Save ONNX Model
    with open(onnx_path, "wb") as f:
        f.write(onnx_model.SerializeToString())
    print(f"Success! Highly optimized ONNX model saved to: {onnx_path}")


if __name__ == "__main__":
    train_and_export()
