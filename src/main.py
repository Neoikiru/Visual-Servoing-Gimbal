"""
Main entry point for the Tracker application.
Provides a dashboard for monitoring and controlling the tracking system.
"""

import argparse
import logging
import sys

from PySide6.QtCore import Qt, Slot  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
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
from src.utils.csv_logger import CSVLogger
from src.utils.logger import setup_logger

logger = logging.getLogger("Tracker")


# @generated [partially] Gemini 3.1 Pro: QtApplication Structure and signals,
#   CSS style, layout and buttons are generated, as well as comments.
class TrackerDashboard(
    QMainWindow
):  # pylint: disable=too-many-instance-attributes,too-few-public-methods
    """
    Main dashboard window containing video feed, control tabs, and telemetry plots.
    """

    # pylint: disable=too-many-locals,too-many-statements
    def __init__(self, cli_args):
        """Initializes the dashboard UI and starts worker threads."""
        super().__init__()
        self.args = cli_args
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

        h, q, r = self.state.get_tuning()
        self.lbl_horiz = QLabel(f"Horizon: {int(h * 1000)} ms")
        self.sld_horiz = QSlider(Qt.Horizontal)
        self.sld_horiz.setRange(0, 500)
        self.sld_horiz.setValue(int(h * 1000))
        self.lbl_q = QLabel(f"Accel Noise: {int(q)}")
        self.sld_q = QSlider(Qt.Horizontal)
        self.sld_q.setRange(1000, 100000)
        self.sld_q.setValue(int(q))
        self.lbl_r = QLabel(f"Cam Noise: {int(r)}")
        self.sld_r = QSlider(Qt.Horizontal)
        self.sld_r.setRange(1, 500)
        self.sld_r.setValue(int(r))

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

        kp_x, kd_x, kp_y, kd_y = self.state.get_pid()
        self.lbl_kp_x = QLabel(f"Kp_X (Prop): {kp_x}")
        self.sld_kp_x = QSlider(Qt.Horizontal)
        self.sld_kp_x.setRange(0, 500)
        self.sld_kp_x.setValue(int(kp_x * 100))
        self.lbl_kd_x = QLabel(f"Kd_X (Deriv): {kd_x}")
        self.sld_kd_x = QSlider(Qt.Horizontal)
        self.sld_kd_x.setRange(0, 500)
        self.sld_kd_x.setValue(int(kd_x * 100))

        self.lbl_kp_y = QLabel(f"Kp_Y (Prop): {kp_y}")
        self.sld_kp_y = QSlider(Qt.Horizontal)
        self.sld_kp_y.setRange(0, 500)
        self.sld_kp_y.setValue(int(kp_y * 100))
        self.lbl_kd_y = QLabel(f"Kd_Y (Deriv): {kd_y}")
        self.sld_kd_y = QSlider(Qt.Horizontal)
        self.sld_kd_y.setRange(0, 500)
        self.sld_kd_y.setValue(int(kd_y * 100))

        hw_layout.addWidget(self.btn_estop, 0, 0, 1, 2)
        hw_layout.addWidget(self.btn_set_home, 1, 0)
        hw_layout.addWidget(self.btn_go_home, 1, 1)
        hw_layout.addWidget(jog_group, 2, 0, 2, 1)
        hw_layout.addWidget(self.lbl_kp_x, 2, 1)
        hw_layout.addWidget(self.sld_kp_x, 3, 1)
        hw_layout.addWidget(self.lbl_kd_x, 4, 1)
        hw_layout.addWidget(self.sld_kd_x, 5, 1)

        hw_layout.addWidget(self.lbl_kp_y, 6, 1)
        hw_layout.addWidget(self.sld_kp_y, 7, 1)
        hw_layout.addWidget(self.lbl_kd_y, 8, 1)
        hw_layout.addWidget(self.sld_kd_y, 9, 1)

        self.tabs.addTab(tab_estimation, "🧮 Software Tuning")
        self.tabs.addTab(tab_hardware, "⚙️ Hardware / PID")

        self.lbl_inspector = QLabel("📍 Inspector: Click video to inspect pixels")
        self.lbl_inspector.setStyleSheet(
            "color: #00FFFF; font-weight: bold; font-size: 14px;"
        )

        # Visual pixel inspector for calibration
        left_column.addWidget(self.lbl_inspector)
        self.video_widget.pixel_clicked.connect(self._on_video_pixel_clicked)

        left_column.addWidget(self.tabs, stretch=2)

        # Right column
        self.plot_widget = TelemetryPlotWidget(max_points=200)

        # main layout
        main_layout.addLayout(left_column, stretch=1)
        main_layout.addWidget(self.plot_widget, stretch=1)

        # Connect sliders to callbacks
        for s in [
            self.sld_horiz,
            self.sld_q,
            self.sld_r,
            self.sld_kp_x,
            self.sld_kd_x,
            self.sld_kp_y,
            self.sld_kd_y,
        ]:
            s.valueChanged.connect(self._on_slider_changed)

        # Connect all buttons to callbacks
        self.btn_save_config.clicked.connect(self._on_save_config_clicked)

        # Joystick
        jog_step = 20
        self.btn_jog_up.clicked.connect(lambda: self._move_gimbal(0, jog_step))
        self.btn_jog_down.clicked.connect(lambda: self._move_gimbal(0, -jog_step))
        self.btn_jog_left.clicked.connect(lambda: self._move_gimbal(-jog_step, 0))
        self.btn_jog_right.clicked.connect(lambda: self._move_gimbal(jog_step, 0))

        # Homing & Safety
        self.btn_set_home.clicked.connect(self._on_set_home_clicked)
        self.btn_go_home.clicked.connect(self._on_go_home_clicked)
        self.btn_estop.clicked.connect(self._on_estop_clicked)

        # Start data recording
        if self.args.video:
            self.csv_logger.start()

        # Gesture control variables
        self.consecutive_frames_open = 0
        self.consecutive_frames_closed = 0
        self.required_frames = 30

        # Setup Threading
        self.threads = []
        self._setup_threads()

    # Callbacks for GUI

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

        self.csv_logger.start()
        self.camera_thread.rewind_requested = True

    def _on_save_config_clicked(self):
        """Pull slider values and save to json"""
        self.state.save_config()
        logger.info("Saved config to disk.")

    def _on_slider_changed(self):
        """Updates internal state when UI sliders are moved."""
        h = self.sld_horiz.value() / 1000.0
        q = float(self.sld_q.value())
        r = float(self.sld_r.value())

        self.lbl_horiz.setText(f"Prediction Horizon: {int(h * 1000)} ms")
        self.lbl_q.setText(f"Process Noise (Accel): {int(q)}")
        self.lbl_r.setText(f"Measurement Noise (R): {int(r)}")

        # Push live tuning
        self.state.update_tuning(h, q, r)

        kp_x = self.sld_kp_x.value() / 100.0
        kd_x = self.sld_kd_x.value() / 100.0

        kp_y = self.sld_kp_y.value() / 100.0
        kd_y = self.sld_kd_y.value() / 100.0

        self.lbl_kp_x.setText(f"Kp_X (Prop): {kp_x:.2f}")
        self.lbl_kd_x.setText(f"Kd_X (Deriv): {kd_x:.2f}")

        self.lbl_kp_y.setText(f"Kp_Y (Prop): {kp_y:.2f}")
        self.lbl_kd_y.setText(f"Kd_Y (Deriv): {kd_y:.2f}")

        self.state.update_pid(kp_x, kd_x, kp_y, kd_y)

    def _move_gimbal(self, steps_x: int, steps_y: int):
        """Sends manual jog commands to the hardware."""
        if self.args.video or self.btn_primary_action.isChecked():
            return
        self.estimation_thread.serial.send_target(steps_x, steps_y)
        logger.info("Manual Jog: X=%s, Y=%s", steps_x, steps_y)

    def _on_set_home_clicked(self):
        """Defines current position as (0,0)."""
        self.estimation_thread.serial.set_current_as_home()

    def _on_go_home_clicked(self):
        """Commands hardware to return to (0,0)."""
        if self.args.video or self.btn_primary_action.isChecked():
            return
        self.estimation_thread.serial.go_home_absolute()

    def _on_estop_clicked(self):
        """Toggles hardware emergency stop state."""
        ser = self.estimation_thread.serial

        if not ser.is_estopped:
            # EMERGENCY STOP
            ser.emergency_stop()

            # Update UI
            self.btn_estop.setText("⚠️ SYSTEM LOCKED - Click to Arm")
            self.btn_estop.setStyleSheet(
                "background-color: #FF8C00; color: black; "
                "font-weight: bold; font-size: 16px; height: 35px;"
            )

            # Disable tracking safety toggle
            if not self.args.video and self.btn_primary_action.isChecked():
                self.btn_primary_action.setChecked(False)
        else:
            # ARM
            ser.arm()

            # Update UI
            self.btn_estop.setText("🛑 E-STOP")
            self.btn_estop.setStyleSheet(
                "background-color: #CC0000; color: white; "
                "font-weight: bold; font-size: 16px; height: 35px;"
            )  # noqa: E501

    # SLOTS (Callbacks for signals)
    @Slot()
    def _on_video_finished(self):
        """Handles video end signal from camera worker."""
        logger.info("Recognized video end.")
        self.csv_logger.save()
        self.btn_primary_action.setText("🔄 Reset And Run Test")
        self.btn_primary_action.setEnabled(True)
        self.btn_primary_action.setStyleSheet(
            "background-color: #006400; color: white;"
        )

    @Slot(dict)
    def _on_telemetry_received(self, data: dict):
        """Hub for incoming telemetry data."""
        # Update the Graphs
        self.plot_widget.update_plots(data)

        # Feed the CSV Logger
        self.csv_logger.add_data(data)

        # Use gesture control
        if not self.args.no_gesture:
            gesture = data.get("gesture", "None")
            if gesture == "Closed":
                self.consecutive_frames_open = 0
                self.consecutive_frames_closed += 1
                if (
                    self.state.is_tracking_enabled()
                    and self.consecutive_frames_closed >= self.required_frames
                ):
                    self.consecutive_frames_open = 0
                    self.consecutive_frames_closed = 0
                    self.state.set_tracking(False)
                    self.btn_primary_action.setChecked(False)

            elif gesture == "Open":
                self.consecutive_frames_open += 1
                self.consecutive_frames_closed = 0
                if (
                    not self.state.is_tracking_enabled()
                    and self.consecutive_frames_open >= self.required_frames
                ):
                    self.consecutive_frames_open = 0
                    self.consecutive_frames_closed = 0
                    self.state.set_tracking(True)
                    self.btn_primary_action.setChecked(True)
            else:
                self.consecutive_frames_open = 0
                self.consecutive_frames_closed = 0

    @Slot(int, int)
    def _on_video_pixel_clicked(self, native_x: int, native_y: int):
        """Displays native coordinates on the UI when the video is clicked."""
        self.lbl_inspector.setText(f"📍 Inspector Selected: X={native_x}, Y={native_y}")

    def _setup_threads(self):
        """Initializes and starts all background worker threads."""
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


def main():
    """Main application launcher."""
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
    parser.add_argument(
        "--feedforward",
        action="store_false",
        help="Disables FeedForward compensation",
    )
    parser.add_argument(
        "--no-gesture",
        action="store_true",
        help="Disables Gesture control",
    )

    args = parser.parse_args()

    if args.video:
        args.debug = True

    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logger(log_level=log_level)

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
    logger.info("Application terminated with exit code %s.", exit_code)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
