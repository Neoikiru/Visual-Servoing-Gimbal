import json
import logging
from pathlib import Path

logger = logging.getLogger("Tracker")


class ConfigManager:
    def __init__(self, filepath: str = "data/calibration/config.json"):
        self.filepath = Path(filepath)
        self.config = self._default_config()
        self.load()

    def _default_config(self):
        return {
            "kalman": {"horizon": 0.15, "q_accel": 50000.0, "r_noise": 100.0},
            "pid": {"kp": 1.0, "kd": 0.1},
            "hardware": {"steps_per_pixel_x": 0.45, "steps_per_pixel_y": 0.45},
        }

    def load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r") as f:
                    loaded = json.load(f)
                    for category, values in loaded.items():
                        if category in self.config:
                            self.config[category].update(values)
                logger.info(f"Loaded configuration from {self.filepath}")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        else:
            self.save()  # Create the default file

    def save(self):
        try:
            with open(self.filepath, "w") as f:
                json.dump(self.config, f, indent=4)
            logger.info("Configuration saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
