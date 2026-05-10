"""
Configuration Manager
Handles loading and saving of application configuration from/to a JSON file.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("Tracker")


# @generated [partially] Gemini 3.1 Pro: Added comments and docstrings.
class ConfigManager:
    """Manages application settings, including Kalman filter and PID parameters."""

    def __init__(self, filepath: str = "data/calibration/config.json"):
        """
        Initializes the ConfigManager.

        :param filepath: Path to the configuration JSON file.
        """
        self.filepath = Path(filepath)
        self.config = self._default_config()
        self.load()

    def _default_config(self):
        """Returns the default configuration dictionary."""
        return {
            "kalman": {"horizon": 0.15, "q_accel": 50000.0, "r_noise": 100.0},
            "pid": {
                "kp_x": 1.0,
                "kd_x": 0.1,
                "kp_y": 1.0,
                "kd_y": 1.0,
            },
            "hardware": {
                "steps_per_pixel_x": 0.45,
                "steps_per_pixel_y": 0.45,
                "pixels_per_step_x": 0.45,
                "pixels_per_step_y": 0.45,
            },
        }

    def load(self):
        """Loads the configuration from the file, merging with defaults."""
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for category, values in loaded.items():
                        if category in self.config:
                            self.config[category].update(values)
                logger.info("Loaded configuration from %s", self.filepath)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load config: %s", e)
        else:
            self.save()  # Create the default file

    def save(self):
        """Saves the current configuration to the file."""
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuration saved successfully.")
        except OSError as e:
            logger.error("Failed to save config: %s", e)
