import copy
from simulator.motor import Motor
from simulator.state import MotorHiddenState
from simulator.config import DEFAULT_CONFIG


class FactorySimulator:
    def __init__(self, num_motors=5, base_config=DEFAULT_CONFIG):
        self.time = 0
        self.motors = []

        for motor_id in range(num_motors):
            motor = self._create_motor(motor_id, base_config)
            self.motors.append(motor)

    def _create_motor(self, motor_id, base_config):
        """
        Create one motor with a slightly different personality.
        """
        config = copy.deepcopy(base_config)

        # ---- Motor personality (controlled variation) ----
        load_factor = 0.9 + 0.1 * motor_id          # increasing load
        misalignment = 0.02 * motor_id               # increasing misalignment
        decay_scale = 1.0 + 0.15 * motor_id          # faster wear for later motors

        config["base_decay"] *= decay_scale

        state = MotorHiddenState(
            bearing_health=1.0,
            load_factor=load_factor,
            misalignment=misalignment,
            friction_coeff=config["base_friction"]
        )

        motor = Motor(state, config)
        motor.motor_id = motor_id  # attach ID
        return motor

    def step(self):
        """
        Advance all motors by one timestep.
        """
        records = []

        for motor in self.motors:
            sensors = motor.step()
            sensors["time"] = self.time
            sensors["motor_id"] = motor.motor_id
            records.append(sensors)

        self.time += 1
        return records
