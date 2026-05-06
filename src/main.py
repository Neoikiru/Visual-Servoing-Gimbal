import sys

from PySide6.QtCore import QThread
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

from src.perception.worker import TrackingWorker
from src.ui.video_widget import VideoWidget


# @generated [partially] Gemini 3.1 Pro: QtApplication Structure and signals.
class TrackerDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker")
        self.resize(800, 600)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # UI Components
        self.video_widget = VideoWidget()
        layout.addWidget(self.video_widget)

        # Setup Threading
        self.setup_worker()

    def setup_worker(self):
        # Create Worker thread
        self.worker = TrackingWorker(camera_id=4)
        self.thread = QThread()

        # put worker in background thread
        self.worker.moveToThread(self.thread)

        # signals
        self.thread.started.connect(self.worker.run)
        self.worker.frame_ready.connect(self.video_widget.update_frame)

        # start thread
        self.thread.start()

    def closeEvent(self, event):
        """Ensure camera release and the thread dies cleanly"""
        self.worker.stop()
        self.thread.quit()
        self.thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrackerDashboard()
    window.show()
    sys.exit(app.exec())
