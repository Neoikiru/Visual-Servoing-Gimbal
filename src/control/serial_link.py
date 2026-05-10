import logging
import time

import serial

logger = logging.getLogger("Tracker")


class SerialLink:
    def __init__(
        self,
        port: str = "/dev/ttyUSB0",
        baudrate: int = 115200,
        debug_mode: bool = False,
    ):
        self.port = port
        self.baudrate = baudrate
        self.debug_mode = debug_mode
        self.ser = None
        self.is_connected = False

        self.is_estopped = False
        self.steps_from_home_x = 0
        self.steps_from_home_y = 0
        self.max_steps_limit = 1000  # For my own safety (remove in prod)

    def connect(self) -> bool:
        if self.debug_mode:
            logger.info("SERIAL DEBUG MODE: Hardware connection bypassed.")
            self.is_connected = True
            return True

        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.05)
            time.sleep(2)
            logger.info(
                f"Successfully connected to hardware on {self.port} "
                f"at {self.baudrate} baud."
            )
            self.is_connected = True
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to {self.port}: {e}")
            self.is_connected = False

            return False

    def send_target(self, x: int, y: int):
        """Packs the steps into <X,Y> string payload."""
        if not self.is_connected or self.is_estopped:
            return

        # Safeguard check
        predicted_x = self.steps_from_home_x + x
        predicted_y = self.steps_from_home_y + y

        if (
            abs(predicted_x) > self.max_steps_limit
            or abs(predicted_y) > self.max_steps_limit
        ) and not self.debug_mode:
            logger.critical(
                f"Requested ({predicted_x}, {predicted_y}) "
                f"exceeds {self.max_steps_limit} steps."
            )
            return

        self.steps_from_home_x = predicted_x
        self.steps_from_home_y = predicted_y

        payload = f"<{x},{y}>\n"

        if self.debug_mode:
            # Only print occasionally
            if time.time() % 1.0 < 0.01:
                logger.debug(f"[MOCK SERIAL TX] {payload.strip()}")
            return

        try:
            self.ser.write(payload.encode("utf-8"))
        except serial.SerialException as e:
            logger.error(f"Serial write failed: {e}")
            self.is_connected = False

    def go_home_absolute(self):
        """Commands the firmware return to (0,0)."""
        if not self.is_connected or self.is_estopped:
            return

        logger.info("Executing homing sequence.")
        self.steps_from_home_x = 0
        self.steps_from_home_y = 0

        if self.debug_mode:
            logger.debug("[MOCK TX] <HOME>")
            return

        try:
            self.ser.write(b"<HOME>\n")
        except serial.SerialException as e:
            logger.error(f"Serial write failed during homing: {e}")

    def set_current_as_home(self):
        """Tells the hardware to define its current position as (0,0)."""
        if not self.is_connected or self.is_estopped:
            return

        logger.info("Setting current physical orientation as absolute home origin.")
        self.steps_from_home_x = 0
        self.steps_from_home_y = 0

        if self.debug_mode:
            logger.debug("[MOCK TX] <ZERO>")
            return

        try:
            self.ser.write(b"<ZERO>\n")
        except serial.SerialException as e:
            logger.error(f"Serial write failed during zeroing: {e}")

    def emergency_stop(self):
        """Halts microcontroller and stops the motors."""
        self.is_estopped = True
        logger.critical("EMERGENCY STOPPING")
        if self.debug_mode:
            logger.debug("[MOCK SERIAL TX] <STOP>")
            return
        if self.ser and self.ser.is_open:
            self.ser.write("<STOP>\n".encode("utf-8"))

    def arm(self):
        """Arms the motors."""
        self.is_estopped = False
        logger.info("Arming... Hardware control reset.")
        if self.debug_mode:
            logger.debug("[MOCK SERIAL TX] <ARM>")
            return
        if self.ser and self.ser.is_open:
            self.ser.write("<ARM>\n".encode("utf-8"))

    def close(self):
        if self.ser and self.ser.is_open:
            self.emergency_stop()
            self.ser.close()
            logger.info("Serial connection closed.")
        self.is_connected = False
