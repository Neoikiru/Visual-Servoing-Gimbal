"""
Tool: Telemetry Analyzer
Visualizes tracking performance from recorded CSV logs using matplotlib.
"""

import glob
import os
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def find_latest_csv(log_dir="logs"):
    """
    Finds the most recently created CSV file in the specified directory.

    :param log_dir: Directory to search for CSV files.
    :return: Path to the latest CSV file.
    """
    list_of_files = glob.glob(f"{log_dir}/*.csv")
    if not list_of_files:
        raise FileNotFoundError(f"No CSV files found in {log_dir}/")
    latest_file = max(list_of_files, key=os.path.getctime)
    return latest_file


def analyze_telemetry(csv_path=None):
    """
    Loads telemetry data from a CSV and generates analysis plots.

    :param csv_path: Path to the CSV file. If None, the latest file is used.
    """
    if csv_path is None:
        csv_path = find_latest_csv()

    print(f"Analyzing log: {csv_path}")
    df = pd.read_csv(csv_path)

    # Convert timestamps
    df["time_sec"] = df["timestamp"] - df["timestamp"].iloc[0]

    plt.style.use("dark_background")
    fig = plt.figure(figsize=(16, 10))
    fig.canvas.manager.set_window_title(f"Telemetry Analysis: {Path(csv_path).name}")

    # Trajectory
    ax1 = plt.subplot(2, 2, 1)
    ax1.plot(
        df["raw_x"],
        df["raw_y"],
        label="Raw AI",
        color="blue",
        alpha=0.3,
        linestyle="--",
    )
    ax1.plot(
        df["filt_x"], df["filt_y"], label="Kalman Filtered", color="yellow", linewidth=2
    )
    ax1.plot(
        df["future_x"], df["future_y"], label="Predicted Future", color="red", alpha=0.7
    )
    ax1.set_title("2D Spatial Trajectory (Pixels)")
    ax1.invert_yaxis()
    ax1.legend()
    ax1.grid(color="#333333")

    # Y
    ax2 = plt.subplot(2, 2, 2)
    ax2.plot(df["time_sec"], df["raw_y"], label="Raw Y", color="blue", alpha=0.5)
    ax2.plot(
        df["time_sec"], df["filt_y"], label="Filtered Y", color="yellow", linewidth=2
    )
    ax2.plot(
        df["time_sec"], df["future_y"], label="Future Y", color="red", linestyle=":"
    )
    ax2.set_title("Y-Axis Coordinates Over Time")
    ax2.set_xlabel("Time (Seconds)")
    ax2.legend()
    ax2.grid(color="#333333")

    # Latency
    ax3 = plt.subplot(2, 2, 3)
    ax3.hist(df["latency_ms"], bins=40, color="cyan", edgecolor="black")
    ax3.axvline(
        df["latency_ms"].mean(),
        color="magenta",
        linestyle="dashed",
        linewidth=2,
        label=f"Mean: {df['latency_ms'].mean():.1f}ms",
    )
    ax3.set_title("System Latency Distribution")
    ax3.set_xlabel("Latency (ms)")
    ax3.set_ylabel("Frequency")
    ax3.legend()

    # Error
    ax4 = plt.subplot(2, 2, 4)
    ax4.plot(df["time_sec"], df["error_px"], color="magenta")
    ax4.axhline(
        df["error_px"].mean(),
        color="white",
        linestyle="dashed",
        label=f"Mean Error: {df['error_px'].mean():.1f} px",
    )
    ax4.fill_between(df["time_sec"], df["error_px"], color="magenta", alpha=0.2)
    ax4.set_title("Prediction Error vs Real Raw Position")
    ax4.set_xlabel("Time (Seconds)")
    ax4.set_ylabel("Distance (Pixels)")
    ax4.legend()
    ax4.grid(color="#333333")

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    analyze_telemetry()
