<a name="readme-top"></a>

<br />
<div align="center">
 <a href="#">  <img src="/documentation/images/logo.png" alt="Logo" width="80" height="80">
 </a>

<h3 align="center">Visual Servoing Gimbal</h3>

 <p align="center">
    A low-latency, real-time hand tracking gimbal driven by an Python perception engine, 2D Kalman state estimation, and C++ serial slave driver.
</p>
</div>

<details>
 <summary>Table of Contents</summary>
 <ol>
 <li>
 <a href="#about-the-project">About The Project</a>
 <ul>
 <li><a href="#built-with">Built With</a></li>
 </ul>
 </li>
 <li>
 <a href="#getting-started">Getting Started</a>
 <ul>
 <li><a href="#prerequisites">Prerequisites</a></li>
 <li><a href="#installation">Installation</a></li>
 </ul>
 </li>
 <li><a href="#usage">Usage</a></li>
 </ol>
</details>

## About The Project

This project implements a high-speed, closed-loop visual servoing platform designed to track hand in real-time.
By utilizing a camera configuration mounted directly to a two-axis stepper motor gimbal, the system
achieves visual locking while dynamically rejecting sensor noise and AI hallucinations.

### Core Architecture

* **Perception Engine:** A multithreaded pipeline (`PySide6.QtCore.QThread`) decouples
  high-resolution OpenCV frame extraction, MediaPipe AI inference, and control loops into dedicated workers
  communicating through a parameter server (the **SharedState**).
* **Kinematic State Estimation:** A **2D Kalman Filter** tracks positional state vectors with a
  constant-acceleration model, utilizing Mahalanobis distance gating to reject severe coordinate anomalies.
* **Ego-Motion Feedforward:** Solves the phase lag problem by tracking pending
  mechanical steps and continuously bleeding off expected visual canvas shifts directly
  from the Kalman memory matrix, preventing estimator panic.
* **Serial Slave Actuation:** High-speed firmware (`stepper_control.ino`) acts as a hardware actuator,
  taking relative step packages (`<X,Y>`) at 115200 baud while computing high-acceleration
  `AccelStepper`.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Built With

### Hardware Infrastructure

* **Microcontroller:** Arduino Uno R3 (ATmega328P)
* **Actuators:** NEMA 17 Stepper Motors driven by DRV8825 Drivers
* **Sensors:** USB Camera

### Software Stack

* **Python Engine:** `PySide6` (GUI/Threading), `OpenCV` (Perception), `MediaPipe` (AI Inference), `NumPy` (
  Kinematics), `pySerial` (Comms), `pytest` (Verification).
* **C++ Firmware:** Arduino Framework, `AccelStepper` Library.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Getting Started

### Prerequisites

* **Hardware**
* **Software:**
    * Arduino IDE
    * Python 3.14
    * `pip`
    * Git

### Installation

1. **Clone the Repository:**
   ```bash
   git clone https://gitlab.fit.cvut.cz/BI-PYT/B252/bondaan3.git
   cd bondaan3
   git switch semestral
   ```
2. **Initialize the Virtual Environment:**
    ```bash
      python -m venv .venv
      source .venv/bin/activate
      pip install -r requirements.txt
   ```
3. **Deploy Firmware:**
    * Open stepper_control/stepper_control.ino in the Arduino IDE
    * Install the AccelStepper library via the Library Manager.
    * Connect your Arduino Uno, confirm the port, and click Upload

<p align="right">(<a href="#readme-top">back to top</a>)</p>

## Usage

**Launching the Main Dashboard:**

* Launch the primary visual dashboard from your command line. The interface initializes in a safe, hardware-locked
  state (Tracking Disabled).
    ```bash
    python -m src.main [OPTIONS]
     ```
    * **Command Line Arguments (CLI):**

      | Argument 	 | Type 	 | Default      	 | Description                                                                          |
                                    |------------|--------|----------------|--------------------------------------------------------------------------------------|
      | --camera 	 | int  	 | 4            	 | Hardware index for the USB camera device.                                            |
      | --video  	 | str  	 | None         	 | Path to an offline MP4 test file (overrides live --camera capture and sets --debug). |
      | --port   	 | str  	 | /dev/ttyACM0 	 | Serial port endpoint for the connected Arduino hardware.                             |
      | --baud   	 | int  	 | 115200       	 | Communication baudrate (Must match firmware configuration).                          |
      | --debug  	 | Flag 	 | False        	 | Forces execution into Mock Serial mode, completely bypassing hardware checks.        |
      | --no-csv 	 | Flag 	 | False        	 | Disables automated background telemetry logging to disk.                             |

    * Recommended (Without Hardware):
  ```bash
   python -m src.main --camera <camera index> --debug
  ```
* **Additional Pipeline Scripts**

  **The project also contains standalone scripts located in the scripts/ directory for calibration, AI training, and
  post-flight analysis:**

    * Extracts internal camera distortion matrices.
      ```bash 
      python -m scripts.01_calibrate_camera
      ```
    * Captures tagged feature sets for custom hand gestures.
      ```bash
      python -m scripts.02_collect_gesture_data
      ```
    * Trains custom gesture classification models.
      ```bash
      python -m scripts.03_train_gesture_model
      ```
    * Runs live ONNX model inference for testing purposes.
      ```bash
      python -m scripts.04_test_gesture_model
      ```
    * Parses generated CSV flight logs to plot trajectories, latency and error.
      ```bash
      python -m scripts.05_analyze_telemetry
      ```

* **Running the Verification Suite:**
   ```bash
   pytest tests/ -v 
   ```

<p align="right">(<a href="#readme-top">back to top</a>)</p>
