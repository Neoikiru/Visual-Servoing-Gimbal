import collections

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Slot
from PySide6.QtWidgets import QVBoxLayout, QWidget


# @generated [all] Gemini 3.1 Pro:
#   Prompt: Write a plot widget this PySide6 app to plot following data...
class TelemetryPlotWidget(QWidget):
    def __init__(self, max_points: int = 100):
        super().__init__()
        self.max_points = max_points

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Plot
        self.plot_graph = pg.PlotWidget(
            title="X-Axis Tracking: Raw vs Filtered vs Future"
        )
        self.plot_graph.setBackground("k")
        self.plot_graph.showGrid(x=True, y=True, alpha=0.3)
        self.plot_graph.setLabel("left", "Pixel Position (X)")
        self.plot_graph.setLabel("bottom", "Time (Frames)")
        self.plot_graph.addLegend()
        layout.addWidget(self.plot_graph)

        # Data Buffers
        self.time_data = collections.deque(maxlen=self.max_points)
        self.raw_x_data = collections.deque(maxlen=self.max_points)
        self.filt_x_data = collections.deque(maxlen=self.max_points)
        self.future_x_data = collections.deque(maxlen=self.max_points)
        self.frame_count = 0

        # Create Lines
        pen_raw = pg.mkPen(
            color=(0, 0, 255), width=2, style=pg.QtCore.Qt.DashLine
        )  # Blue dashed
        pen_filt = pg.mkPen(color=(255, 255, 0), width=3)  # Yellow solid
        pen_fut = pg.mkPen(color=(255, 0, 0), width=2)  # Red solid

        self.line_raw = self.plot_graph.plot(name="Raw Measurement", pen=pen_raw)
        self.line_filt = self.plot_graph.plot(name="Kalman Filtered", pen=pen_filt)
        self.line_fut = self.plot_graph.plot(name="Predicted Future", pen=pen_fut)

    @Slot(dict)
    def update_plots(self, data: dict):
        """Receives the telemetry dictionary from the background worker
        and updates lines.
        """
        self.frame_count += 1

        # save new data
        self.time_data.append(self.frame_count)
        self.raw_x_data.append(data["raw_x"])
        self.filt_x_data.append(data["filt_x"])
        self.future_x_data.append(data["future_x"])

        # Convert to numpy for fast PyQtGraph drawing
        t_arr = np.array(self.time_data)

        self.line_raw.setData(t_arr, np.array(self.raw_x_data))
        self.line_filt.setData(t_arr, np.array(self.filt_x_data))
        self.line_fut.setData(t_arr, np.array(self.future_x_data))
