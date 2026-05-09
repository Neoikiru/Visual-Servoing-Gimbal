import argparse
import logging
import sys

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from src.control.estimation_worker import EstimationWorker
from src.core.state import SystemState
from src.perception.ai_worker import AIWorker
from src.perception.camera_worker import CameraWorker
from src.ui.plot_widget import TelemetryPlotWidget
from src.ui.video_widget import VideoWidget
from src.utils.logger import setup_logger


# @generated [partially] Gemini 3.1 Pro: QtApplication Structure and signals hints.
class TrackerDashboard(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.setWindowTitle("Tracker")
        self.resize(1200, 700)

        self.setStyleSheet("""
            QMainWindow { background-color: #0E0E0E; }
            QWidget { color: #E0E0E0; font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; }
            QGroupBox { border: 1px solid #333333; border-radius: 6px; margin-top: 15px; font-weight: bold; }
            QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; color: #00A5FF; }
            QSlider::groove:horizontal { border: 1px solid #222; height: 6px; background: #1A1A1A; border-radius: 3px; }
            QSlider::handle:horizontal { background: #00A5FF; width: 16px; margin: -5px 0; border-radius: 8px; }
            QSlider::handle:horizontal:hover { background: #00C8FF; }
        """)  # noqa: E501

        # Main Data Storage
        self.state = SystemState()

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(15)

        left_column = QVBoxLayout()
        self.video_widget = VideoWidget()
        left_column.addWidget(self.video_widget, stretch=3)

        # Control
        control_panel = QGroupBox("Kalman Tuning & Live Metrics")
        control_layout = QGridLayout(control_panel)

        # Sliders
        self.lbl_horiz = QLabel("Horizon: 150 ms")
        self.sld_horiz = QSlider(Qt.Horizontal)
        self.sld_horiz.setRange(0, 500)
        self.sld_horiz.setValue(150)

        self.lbl_q = QLabel("Accel Noise (Q): 50000")
        self.sld_q = QSlider(Qt.Horizontal)
        self.sld_q.setRange(1000, 100000)
        self.sld_q.setValue(50000)

        self.lbl_r = QLabel("Cam Noise (R): 100")
        self.sld_r = QSlider(Qt.Horizontal)
        self.sld_r.setRange(1, 500)
        self.sld_r.setValue(100)

        # Grid Layout for the Control Panel
        control_layout.addWidget(self.lbl_horiz, 1, 0)
        control_layout.addWidget(self.sld_horiz, 1, 1)

        control_layout.addWidget(self.lbl_q, 2, 0)
        control_layout.addWidget(self.sld_q, 2, 1)

        control_layout.addWidget(self.lbl_r, 3, 0)
        control_layout.addWidget(self.sld_r, 3, 1)

        for slider in [self.sld_horiz, self.sld_q, self.sld_r]:
            slider.valueChanged.connect(self._on_slider_changed)

        left_column.addWidget(control_panel, stretch=1)

        # Right column
        self.plot_widget = TelemetryPlotWidget(max_points=200)

        # main layout
        main_layout.addLayout(left_column, stretch=1)
        main_layout.addWidget(self.plot_widget, stretch=1)

        # Setup Threading
        self.threads = []
        self._setup_threads()

    def _on_slider_changed(self):
        h = self.sld_horiz.value() / 1000.0
        q = float(self.sld_q.value())
        r = float(self.sld_r.value())

        self.lbl_horiz.setText(f"Prediction Horizon: {int(h * 1000)} ms")
        self.lbl_q.setText(f"Process Noise (Accel): {int(q)}")
        self.lbl_r.setText(f"Measurement Noise (R): {int(r)}")

        # Push live tuning to the Spine
        self.state.update_tuning(h, q, r)

    def _setup_threads(self):
        # Create  Workers
        cam_source = self.args.video if self.args.video else self.args.camera
        self.camera_thread = CameraWorker(self.state, camera_id=cam_source)

        self.ai_thread = AIWorker(self.state)
        self.estimation_thread = EstimationWorker(self.state, self.args)

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
    parser = argparse.ArgumentParser(description="Tracking System")
    parser.add_argument(
        "--camera", type=int, default=4, help="Camera device index (default: 4)"
    )
    parser.add_argument(
        "--video",
        type=str,
        default=None,
        help="Path to a test video file (overrides --camera)",
    )
    parser.add_argument(
        "--port", type=str, default="/dev/ttyACM0", help="Arduino Serial Port"
    )
    parser.add_argument("--baud", type=int, default=115200, help="Serial Baudrate")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Run without physical hardware (Mock Serial)",
    )

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger(log_level=log_level)

    logger.info("Initializing Application...")
    if args.debug:
        logger.debug("Debug mode activated via CLI.")

    app = QApplication(sys.argv)
    window = TrackerDashboard(args)
    window.show()

    exit_code = app.exec()
    logger.info(f"Application terminated with exit code {exit_code}.")
    sys.exit(exit_code)
