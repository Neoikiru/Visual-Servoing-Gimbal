import time

import serial

from src.utils.logger import logger


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
        """Packs the coordinates into <X,Y> string payload."""
        if not self.is_connected:
            return

        payload = f"<{x},{y}>\n"

        if self.debug_mode:
            # Only print occasionally
            if time.time() % 1.0 < 0.05:
                logger.debug(f"[MOCK SERIAL TX] {payload.strip()}")
            return

        try:
            self.ser.write(payload.encode("utf-8"))
        except serial.SerialException as e:
            logger.error(f"Serial write failed: {e}")
            self.is_connected = False

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            logger.info("Serial connection closed.")
        self.is_connected = False
