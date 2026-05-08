import time

from PySide6.QtCore import QThread

from src.core.state import SystemState
from src.perception.camera import Camera
from src.utils.logger import logger


class CameraWorker(QThread):
    def __init__(self, state: SystemState, camera_id: int = 4):
        super().__init__()
        self.state = state
        self.camera_id = camera_id

    def run(self):
        logger.info("Camera Thread Started.")
        camera = Camera(camera_id=self.camera_id)

        while self.state.check_running():
            ret, frame = camera.read()
            if not ret:
                time.sleep(0.01)
                continue

            # Push the newest frame
            self.state.set_frame(frame)

            time.sleep(0.005)

        camera.release()
        logger.info("Camera Thread Stopped.")
