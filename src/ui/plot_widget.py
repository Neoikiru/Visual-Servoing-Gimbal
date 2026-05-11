"""
UI widget for displaying real-time telemetry plots.
"""

import collections

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, Slot  # pylint: disable=no-name-in-module
from PySide6.QtWidgets import (  # pylint: disable=no-name-in-module
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)


# @generated [partially] Gemini 3.1 Pro: Generated full original plotter widget,
#   later modified by me.
class TelemetryPlotWidget(QWidget):  # pylint: disable=too-many-instance-attributes
    """
    Widget that uses pyqtgraph to render live telemetry data such as:
        position tracking (X), latency (ms), and spatial error (pixels).
    """

    def __init__(self, max_points: int = 100):
        """Initializes the plot widget with layout and data buffers."""
        super().__init__()
        self.max_points = max_points

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Stats
        stats_layout = QHBoxLayout()
        self.lbl_avg_lat = QLabel("Avg Latency: -- ms")
        self.lbl_avg_err = QLabel("Avg Error: -- px")

        self.lbl_avg_lat.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #00FFFF;"
        )
        self.lbl_avg_err.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #FF00FF;"
        )
        self.lbl_avg_lat.setAlignment(Qt.AlignCenter)
        self.lbl_avg_err.setAlignment(Qt.AlignCenter)

        stats_layout.addWidget(self.lbl_avg_lat)
        stats_layout.addWidget(self.lbl_avg_err)
        layout.addLayout(stats_layout)

        # PyQtGraph layout
        self.glw = pg.GraphicsLayoutWidget()
        layout.addWidget(self.glw)

        # Trajectory Plot
        self.p_traj = self.glw.addPlot(
            title="X-Axis Tracking: Raw vs Filtered vs Future"
        )
        self.p_traj.showGrid(x=True, y=True, alpha=0.3)
        self.p_traj.setLabel("left", "Pixel Position (X)")
        self.p_traj.setLabel("bottom", "Time (Frames)")
        self.p_traj.addLegend()

        # pylint: disable=no-member
        self.line_raw = self.p_traj.plot(
            name="Raw",
            pen=pg.mkPen(color=(0, 0, 255), width=2, style=pg.QtCore.Qt.DashLine),
        )
        self.line_filt = self.p_traj.plot(
            name="Filtered", pen=pg.mkPen(color=(255, 255, 0), width=3)
        )
        self.line_fut = self.p_traj.plot(
            name="Future", pen=pg.mkPen(color=(255, 0, 0), width=2)
        )

        self.glw.nextRow()

        # Latency Plot
        self.p_lat = self.glw.addPlot(title="Latency (ms)")
        self.p_lat.showGrid(x=True, y=True, alpha=0.3)
        self.line_lat = self.p_lat.plot(
            name="Latency", pen=pg.mkPen(color="c", width=2)
        )

        self.glw.nextRow()

        # Spatial Err Plot
        self.p_err = self.glw.addPlot(title="Error (Pixels)")
        self.p_err.showGrid(x=True, y=True, alpha=0.3)
        self.line_err = self.p_err.plot(name="Err", pen=pg.mkPen(color="m", width=2))

        # Data Buffers
        self.time_data = collections.deque(maxlen=self.max_points)
        self.raw_x_data = collections.deque(maxlen=self.max_points)
        self.filt_x_data = collections.deque(maxlen=self.max_points)
        self.future_x_data = collections.deque(maxlen=self.max_points)
        self.lat_data = collections.deque(maxlen=self.max_points)
        self.err_data = collections.deque(maxlen=self.max_points)
        self.frame_count = 0

    @Slot(dict)
    def update_plots(self, data: dict):
        """Receives the telemetry dictionary and updates plot lines."""
        self.frame_count += 1
        self.time_data.append(self.frame_count)

        # save new data
        self.raw_x_data.append(data["raw_x"])
        self.filt_x_data.append(data["filt_x"])
        self.future_x_data.append(data["future_x"])
        self.lat_data.append(data["latency"])
        self.err_data.append(data.get("prediction_error", 0.0))

        # Convert to numpy for fast PyQtGraph drawing
        t_arr = np.array(self.time_data)

        self.line_raw.setData(t_arr, np.array(self.raw_x_data))
        self.line_filt.setData(t_arr, np.array(self.filt_x_data))
        self.line_fut.setData(t_arr, np.array(self.future_x_data))
        self.line_lat.setData(t_arr, np.array(self.lat_data))
        self.line_err.setData(t_arr, np.array(self.err_data))

        if len(self.lat_data) > 0:
            avg_lat = sum(self.lat_data) / len(self.lat_data)
            avg_err = sum(self.err_data) / len(self.err_data)
            self.lbl_avg_lat.setText(f"Avg Latency: {avg_lat:.1f} ms")
            self.lbl_avg_err.setText(f"Avg Error: {avg_err:.1f} px")

    @Slot()
    def clear_plots(self):
        """Wipes all data buffers and resets the frame count."""
        self.time_data.clear()
        self.raw_x_data.clear()
        self.filt_x_data.clear()
        self.future_x_data.clear()
        self.lat_data.clear()
        self.err_data.clear()
        self.frame_count = 0

        # Redraw to clear the screen
        empty = np.array([])
        self.line_raw.setData(empty, empty)
        self.line_filt.setData(empty, empty)
        self.line_fut.setData(empty, empty)
        self.line_lat.setData(empty, empty)
        self.line_err.setData(empty, empty)
