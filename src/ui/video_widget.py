"""
UI widget for displaying OpenCV video frames in a Qt label.
"""

import logging

import cv2
import numpy as np
from PySide6.QtCore import Qt, Signal, Slot  # pylint: disable=no-name-in-module
from PySide6.QtGui import QImage, QPixmap  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import QLabel  # pylint: disable=no-name-in-module

logger = logging.getLogger("Tracker")


# @generated [all] Gemini 3.1 Pro:
#   Prompt: Write a video widget this PySide6 app to display OpenCV frames...
#   Prompt: Create a method to capture mouse clicks and log them.
class VideoWidget(QLabel):
    """
    Custom QLabel for rendering OpenCV frames and capturing mouse interaction.
    """

    pixel_clicked = Signal(int, int)

    def __init__(self):
        """Initializes the video widget with center alignment and default size."""
        super().__init__()
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumSize(640, 480)
        self.setStyleSheet("background-color: black;")

        self.native_width = 1280.0
        self.native_height = 720.0

        self.setCursor(Qt.CrossCursor)

    @Slot(np.ndarray)
    def update_frame(self, frame: np.ndarray):
        """
        Receives an OpenCV frame, converts it to a QPixmap, and displays it.
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

    def mousePressEvent(self, event):
        """Catches UI mouse clicks and maps them to video coordinates."""
        if not self.pixmap() or self.pixmap().isNull():
            return

        # geometry of the rendered pixmap inside the QLabel
        pixmap_rect = self.pixmap().rect()

        # Calculate letterbox offsets
        offset_x = (self.width() - pixmap_rect.width()) / 2.0
        offset_y = (self.height() - pixmap_rect.height()) / 2.0

        # Get click position
        click_x = event.position().x() - offset_x
        click_y = event.position().y() - offset_y

        # Check if the click is inside the video area
        if 0 <= click_x <= pixmap_rect.width() and 0 <= click_y <= pixmap_rect.height():
            # Scale UI pixels to Camera pixels
            scale_x = self.native_width / float(pixmap_rect.width())
            scale_y = self.native_height / float(pixmap_rect.height())

            native_x = int(click_x * scale_x)
            native_y = int(click_y * scale_y)

            logger.debug(
                "Clicked UI -> Native Coordinate: (%s, %s)", native_x, native_y
            )
            self.pixel_clicked.emit(native_x, native_y)

        super().mousePressEvent(event)
