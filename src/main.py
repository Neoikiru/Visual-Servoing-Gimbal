import sys

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)

from src.control.estimation_worker import EstimationWorker
from src.core.state import SystemState
from src.perception.ai_worker import AIWorker
from src.perception.camera_worker import CameraWorker
from src.ui.plot_widget import TelemetryPlotWidget
from src.ui.video_widget import VideoWidget
from src.utils.logger import logger


# @generated [partially] Gemini 3.1 Pro: QtApplication Structure and signals hints.
class TrackerDashboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tracker")
        self.resize(1200, 700)

        # Main Data Storage
        self.state = SystemState()

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # UI Components
        self.video_widget = VideoWidget()
        self.plot_widget = TelemetryPlotWidget(max_points=150)

        layout.addWidget(self.video_widget, stretch=2)
        layout.addWidget(self.plot_widget, stretch=1)

        # Setup Threading
        self.threads = []
        self._setup_threads()

    def _setup_threads(self):
        # Create  Workers
        self.camera_thread = CameraWorker(self.state, camera_id=4)
        self.ai_thread = AIWorker(self.state)
        self.estimation_thread = EstimationWorker(self.state)

        # Connect Signals
        self.estimation_thread.frame_ready.connect(self.video_widget.update_frame)
        self.estimation_thread.telemetry_ready.connect(self.plot_widget.update_plots)

        # Add to pool
        self.threads = [self.camera_thread, self.ai_thread, self.estimation_thread]

        # Start
        for thread in self.threads:
            thread.start()

        logger.info("System initialized.")

    def closeEvent(self, event):
        """Ensure camera release and the thread dies cleanly"""
        logger.info("Shutting Down...")
        self.state.stop()

        for thread in self.threads:
            thread.quit()
            thread.wait()

        logger.info("Shutdown complete.")
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TrackerDashboard()
    window.show()
    sys.exit(app.exec())
