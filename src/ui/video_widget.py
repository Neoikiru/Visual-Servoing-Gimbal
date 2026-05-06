import cv2
import numpy as np
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel


# @generated [all] Gemini 3.1 Pro:
#   Prompt: Write a video widget this PySide6 app to display OpenCV frames...
class VideoWidget(QLabel):
    def __init__(self):
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: black;")

    @Slot(np.ndarray)
    def update_frame(self, frame: np.ndarray):
        """
        Receives an OpenCV frame ,converts it to a QPixmap, and displays it.
        """
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w

        # Convert to QImage
        q_img = QImage(
            rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        )

        # Scale to fit the label while keeping aspect ratio
        pixmap = QPixmap.fromImage(q_img)
        self.setPixmap(
            pixmap.scaled(
                self.width(),
                self.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
