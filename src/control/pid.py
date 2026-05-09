import time


class PDController:
    def __init__(self, kp: float, kd: float):
        self.kp = kp
        self.kd = kd
        self.prev_error = 0.0
        self.last_time = time.time()

    def compute(self, error: float, current_time: float) -> float:
        dt = current_time - self.last_time
        if dt <= 0.0:
            dt = 0.016

        # Derivative
        derivative = (error - self.prev_error) / dt

        # PD Output
        output = (self.kp * error) + (self.kd * derivative)

        self.prev_error = error
        self.last_time = current_time

        return output

    def update_gains(self, kp: float, kd: float):
        self.kp = kp
        self.kd = kd

    def reset(self):
        self.prev_error = 0.0
        self.last_time = time.time()
