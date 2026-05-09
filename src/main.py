import argparse
import logging
import sys

from PySide6.QtCore import Qt, Slot
from PySide6.QtWidgets import (
    QApplication,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from src.control.estimation_worker import EstimationWorker
from src.core.state import SystemState
from src.perception.ai_worker import AIWorker
from src.perception.camera_worker import CameraWorker
from src.ui.plot_widget import TelemetryPlotWidget
from src.ui.video_widget import VideoWidget
from src.utils.config import ConfigManager
from src.utils.csv_logger import CSVLogger
from src.utils.logger import setup_logger


# @generated [partially] Gemini 3.1 Pro: QtApplication Structure and signals hints.
#   CSS style, layout and buttons are generated.
class TrackerDashboard(QMainWindow):
    def __init__(self, args):
        super().__init__()
        self.args = args
        self.setWindowTitle("Tracker")
        self.resize(1400, 900)

        self.setStyleSheet("""
            QMainWindow { background-color: #0E0E0E; }
            QWidget { font-family: 'Segoe UI', Arial, sans-serif; font-size: 14px; }
            QLabel { color: #E0E0E0; background-color: transparent; }
            QTabWidget::pane { border: 1px solid #333333; background-color: #121212; border-radius: 4px; }
            QTabBar::tab { background: #1E1E1E; color: #AAAAAA; padding: 8px 20px; border-top-left-radius: 4px; border-top-right-radius: 4px; }
            QTabBar::tab:selected { background: #00A5FF; color: #000000; font-weight: bold; }
            QSlider::groove:horizontal { border: 1px solid #222; height: 6px; background: #1A1A1A; border-radius: 3px; }
            QSlider::handle:horizontal { background: #00A5FF; width: 16px; margin: -5px 0; border-radius: 8px; }
            QSlider::handle:horizontal:hover { background: #00C8FF; }
            QPushButton { background-color: #2D2D2D; color: #FFFFFF; border: 1px solid #555; border-radius: 4px; padding: 6px; font-weight: bold; }
            QPushButton:hover { background-color: #3D3D3D; }
        """)  # noqa: E501

        # Main Data Storage
        self.state = SystemState()
        self.config_mgr = ConfigManager()
        self.csv_logger = CSVLogger(disabled=self.args.no_csv)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(15, 15, 15, 15)

        left_column = QVBoxLayout()
        self.video_widget = VideoWidget()
        left_column.addWidget(self.video_widget, stretch=3)

        # Tab Widget (Controls)
        self.tabs = QTabWidget()

        # Tab 1
        tab_estimation = QWidget()
        est_layout = QGridLayout(tab_estimation)

        c = self.config_mgr.config["kalman"]
        self.lbl_horiz = QLabel(f"Horizon: {int(c['horizon'] * 1000)} ms")
        self.sld_horiz = QSlider(Qt.Horizontal)
        self.sld_horiz.setRange(0, 500)
        self.sld_horiz.setValue(int(c["horizon"] * 1000))
        self.lbl_q = QLabel(f"Accel Noise: {int(c['q_accel'])}")
        self.sld_q = QSlider(Qt.Horizontal)
        self.sld_q.setRange(1000, 100000)
        self.sld_q.setValue(int(c["q_accel"]))
        self.lbl_r = QLabel(f"Cam Noise: {int(c['r_noise'])}")
        self.sld_r = QSlider(Qt.Horizontal)
        self.sld_r.setRange(1, 500)
        self.sld_r.setValue(int(c["r_noise"]))

        # Button logic
        if self.args.video:
            self.btn_primary_action = QPushButton("▶ Playing...")
            self.btn_primary_action.setEnabled(False)
            self.btn_primary_action.setStyleSheet(
                "background-color: #006400; color: white;"
            )
            self.btn_primary_action.clicked.connect(self._on_reset_run_clicked)
        else:
            self.btn_primary_action = QPushButton("🎯 Enable Tracking")
            self.btn_primary_action.setCheckable(True)
            self.btn_primary_action.setStyleSheet("""
                QPushButton:checked { background-color: #006400; color: white; border: 2px solid #00FF00; }
                QPushButton:!checked { background-color: #444444; color: white; }
            """)  # noqa: E501
            self.btn_primary_action.toggled.connect(self._on_tracking_toggled)

        self.btn_save_config = QPushButton("💾 Save Config")

        est_layout.addWidget(self.lbl_horiz, 0, 0)
        est_layout.addWidget(self.sld_horiz, 0, 1)
        est_layout.addWidget(self.lbl_q, 1, 0)
        est_layout.addWidget(self.sld_q, 1, 1)
        est_layout.addWidget(self.lbl_r, 2, 0)
        est_layout.addWidget(self.sld_r, 2, 1)
        est_layout.addWidget(self.btn_primary_action, 3, 0)
        est_layout.addWidget(self.btn_save_config, 3, 1)

        # Tab 2
        tab_hardware = QWidget()
        hw_layout = QGridLayout(tab_hardware)

        self.btn_estop = QPushButton("🛑 E-STOP")
        self.btn_estop.setStyleSheet(
            "background-color: #CC0000; color: white; font-size: 16px; height: 35px;"
        )

        self.btn_set_home = QPushButton("📍 Set Current as Home")
        self.btn_go_home = QPushButton("🏠 Go Home (0,0)")

        # Control Arrows
        jog_group = QGroupBox()
        jog_layout = QGridLayout(jog_group)
        self.btn_jog_up = QPushButton("▲")
        self.btn_jog_up.setFixedWidth(40)
        self.btn_jog_down = QPushButton("▼")
        self.btn_jog_down.setFixedWidth(40)
        self.btn_jog_left = QPushButton("◀")
        self.btn_jog_left.setFixedWidth(40)
        self.btn_jog_right = QPushButton("▶")
        self.btn_jog_right.setFixedWidth(40)

        jog_layout.addWidget(self.btn_jog_up, 0, 1)
        jog_layout.addWidget(self.btn_jog_left, 1, 0)
        jog_layout.addWidget(self.btn_jog_right, 1, 2)
        jog_layout.addWidget(self.btn_jog_down, 2, 1)

        p = self.config_mgr.config["pid"]
        self.lbl_kp = QLabel(f"Kp (Prop): {p['kp']}")
        self.sld_kp = QSlider(Qt.Horizontal)
        self.sld_kp.setRange(0, 500)
        self.sld_kp.setValue(int(p["kp"] * 100))
        self.lbl_kd = QLabel(f"Kd (Deriv): {p['kd']}")
        self.sld_kd = QSlider(Qt.Horizontal)
        self.sld_kd.setRange(0, 500)
        self.sld_kd.setValue(int(p["kd"] * 100))

        hw_layout.addWidget(self.btn_estop, 0, 0, 1, 2)
        hw_layout.addWidget(self.btn_set_home, 1, 0)
        hw_layout.addWidget(self.btn_go_home, 1, 1)
        hw_layout.addWidget(jog_group, 2, 0, 2, 1)
        hw_layout.addWidget(self.lbl_kp, 2, 1)
        hw_layout.addWidget(self.sld_kp, 3, 1)
        hw_layout.addWidget(self.lbl_kd, 4, 1)
        hw_layout.addWidget(self.sld_kd, 5, 1)

        self.tabs.addTab(tab_estimation, "🧮 Software Tuning")
        self.tabs.addTab(tab_hardware, "⚙️ Hardware / PID")

        left_column.addWidget(self.tabs, stretch=1)

        # Right column
        self.plot_widget = TelemetryPlotWidget(max_points=200)

        # main layout
        main_layout.addLayout(left_column, stretch=1)
        main_layout.addWidget(self.plot_widget, stretch=1)

        for s in [self.sld_horiz, self.sld_q, self.sld_r, self.sld_kp, self.sld_kd]:
            s.valueChanged.connect(self._on_slider_changed)

        self.btn_save_config.clicked.connect(self._on_save_config_clicked)

        # Start data recording
        if self.args.video:
            self.csv_logger.start()

        # Setup Threading
        self.threads = []
        self._setup_threads()

    def _on_tracking_toggled(self, checked: bool):
        """Called when the 'Enable Tracking' button is toggled in Live Mode."""
        self.state.set_tracking(checked)
        if checked:
            logger.info("Hardware Tracking Enabled.")
            self.csv_logger.start()
            self.btn_primary_action.setText("🔴 Disable Tracking")
        else:
            logger.info("Hardware Tracking Disabled.")
            self.csv_logger.save()
            self.btn_primary_action.setText("🎯 Enable Tracking")

    def _on_save_config_clicked(self):
        """Pull slider values and save to json"""
        self.config_mgr.config["kalman"]["horizon"] = self.sld_horiz.value() / 1000.0
        self.config_mgr.config["kalman"]["q_accel"] = float(self.sld_q.value())
        self.config_mgr.config["kalman"]["r_noise"] = float(self.sld_r.value())
        self.config_mgr.save()

    def _on_slider_changed(self):
        h = self.sld_horiz.value() / 1000.0
        q = float(self.sld_q.value())
        r = float(self.sld_r.value())

        self.lbl_horiz.setText(f"Prediction Horizon: {int(h * 1000)} ms")
        self.lbl_q.setText(f"Process Noise (Accel): {int(q)}")
        self.lbl_r.setText(f"Measurement Noise (R): {int(r)}")

        # Push live tuning
        self.state.update_tuning(h, q, r)

        kp = self.sld_kp.value() / 100.0
        kd = self.sld_kd.value() / 100.0

        self.lbl_kp.setText(f"Kp (Prop): {kp:.2f}")
        self.lbl_kd.setText(f"Kd (Deriv): {kd:.2f}")

    @Slot()
    def _on_video_finished(self):
        logger.info("Recognized video end.")
        self.csv_logger.save()
        self.btn_primary_action.setText("🔄 Reset And Run Test")
        self.btn_primary_action.setEnabled(True)
        self.btn_primary_action.setStyleSheet(
            "background-color: #006400; color: white;"
        )

    def _on_reset_run_clicked(self):
        """Test Cycle Reset"""
        logger.info("Test Cycle Reset Initiated.")

        # Lock UI
        self.btn_primary_action.setText("▶ Playing...")
        self.btn_primary_action.setEnabled(False)
        self.btn_primary_action.setStyleSheet(
            "background-color: #555555; color: white;"
        )

        self.plot_widget.clear_plots()
        self.state.request_reset = True
        self.state.set_paused(False)

        if self.args.video:
            self.csv_logger.start()
            self.camera_thread.rewind_requested = True

    @Slot(dict)
    def _on_telemetry_received(self, data: dict):
        """Hub for incoming telemetry data."""
        # Update the Graphs
        self.plot_widget.update_plots(data)

        # Feed the CSV Logger
        self.csv_logger.add_data(data)

    def _setup_threads(self):
        # Create  Workers

        self.camera_thread = CameraWorker(
            self.state, camera_id=self.args.camera, video_path=self.args.video
        )
        self.ai_thread = AIWorker(self.state)
        self.estimation_thread = EstimationWorker(self.state, self.args)

        # Connect Signals
        self.estimation_thread.frame_ready.connect(self.video_widget.update_frame)
        self.estimation_thread.telemetry_ready.connect(self._on_telemetry_received)
        if self.args.video:
            self.camera_thread.video_finished.connect(self._on_video_finished)

        # Add to pool
        self.threads = [self.camera_thread, self.ai_thread, self.estimation_thread]

        # Start
        for thread in self.threads:
            thread.start()

        logger.info("System initialized.")

    def closeEvent(self, event):
        """Ensure camera release and the thread dies cleanly"""
        logger.info("Shutting Down...")
        self.csv_logger.save()
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
    parser.add_argument(
        "--no-csv",
        action="store_true",
        help="Disables CSV logging",
    )

    args = parser.parse_args()

    if args.video:
        args.debug = True

    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger(log_level=log_level)

    logger.info("Initializing Application...")
    if args.debug:
        logger.debug("Debug mode activated via CLI.")

    if args.video:
        logger.debug(
            "[SAFETY] Video Mode detected. Hardware Serial forced to DEBUG mode."
        )

    app = QApplication(sys.argv)
    window = TrackerDashboard(args)
    window.show()

    exit_code = app.exec()
    logger.info(f"Application terminated with exit code {exit_code}.")
    sys.exit(exit_code)
