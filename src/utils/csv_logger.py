# @generated [partially] Gemini 3.1 Pro: comments and string refactoring.
"""
CSV Telemetry Logger
Logs system telemetry and performance metrics to a CSV file.
"""

import csv
import logging
import time
from pathlib import Path

logger = logging.getLogger("Tracker")


# @generated [partially] Gemini 3.1 Pro: Added comments and docstrings.
class CSVLogger:
    """Handles buffered logging of telemetry data to CSV files."""

    def __init__(self, log_dir="logs", disabled=False):
        """
        Initializes the CSVLogger.

        :param log_dir: Directory where log files will be saved.
        :param disabled: If True, logging operations are ignored.
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.buffer = []
        self.headers = [
            "timestamp",
            "raw_x",
            "filt_x",
            "future_x",
            "raw_y",
            "filt_y",
            "future_y",
            "latency_ms",
            "error_px",
        ]
        self.is_recording = False
        self.disabled = disabled
        if disabled:
            logger.info("CSV logger disabled.")

    def start(self):
        """Clears the buffer and begins recording."""
        if self.disabled:
            return

        self.buffer.clear()
        self.is_recording = True
        logger.info("CSV Recording started.")

    def add_data(self, data: dict):
        """
        Appends a row to the buffer if recording is active.

        :param data: Dictionary containing telemetry values.
        """
        if not self.is_recording or self.disabled:
            return

        row = {
            "timestamp": time.time(),
            "raw_x": data.get("raw_x", 0.0),
            "filt_x": data.get("filt_x", 0.0),
            "future_x": data.get("future_x", 0.0),
            "raw_y": data.get("raw_y", 0.0),
            "filt_y": data.get("filt_y", 0.0),
            "future_y": data.get("future_y", 0.0),
            "latency_ms": data.get("latency", 0.0),
            "error_px": data.get("error", 0.0),
        }
        self.buffer.append(row)

    def save(self):
        """Writes the buffer to disk and stops recording."""

        if self.disabled:
            return

        if not self.buffer:
            if self.is_recording:
                logger.warning("CSV save requested, but buffer is empty.")
            self.is_recording = False
            return

        self.is_recording = False
        filename = self.log_dir / f"run_{time.strftime('%Y%m%d_%H%M%S')}.csv"

        try:
            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.headers)
                writer.writeheader()
                writer.writerows(self.buffer)
            logger.info(
                "Successfully saved %d frames to %s", len(self.buffer), filename
            )
        except OSError as e:
            logger.error("Failed to save CSV: %s", e)

        self.buffer.clear()
