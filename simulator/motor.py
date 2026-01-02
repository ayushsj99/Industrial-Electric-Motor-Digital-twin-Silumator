from simulator.state import MotorHiddenState
import simulator.physics as phys
from simulator.noise import add_gaussian_noise, add_spike, maybe_drop


class Motor:
    def __init__(self, state: MotorHiddenState, config: dict):
        self.state = state
        self.config = config

        # Observable internal state
        self.temperature = config["ambient_temp"]

        # Sensor drift (bias)
        self.sensor_bias = {
            "temperature": 0.0,
            "vibration": 0.0
        }

    def step(self):
        """
        Advance the motor by one timestep.
        """

        # -------------------------
        # 1. Update hidden health
        # -------------------------
        self.state.bearing_health = phys.update_bearing_health(
            health=self.state.bearing_health,
            base_decay=self.config["base_decay"],
            load=self.state.load_factor,
            misalignment=self.state.misalignment
        )

        self.state.friction_coeff = phys.update_friction(
            base_friction=self.config["base_friction"],
            bearing_health=self.state.bearing_health,
            k_friction=self.config["k_friction"]
        )

        # -------------------------
        # 2. Update temperature
        # -------------------------
        self.temperature = phys.update_temperature(
            temp=self.temperature,
            ambient_temp=self.config["ambient_temp"],
            friction=self.state.friction_coeff,
            load=self.state.load_factor,
            alpha=self.config["alpha"],
            beta=self.config["beta"]
        )

        # -------------------------
        # 3. Ideal (noise-free) sensors
        # -------------------------
        vibration = phys.compute_vibration(
            bearing_health=self.state.bearing_health,
            misalignment=self.state.misalignment,
            v_base=self.config["v_base"],
            k_health=self.config["k_v_health"],
            k_align=self.config["k_v_align"]
        )

        current = phys.compute_current(
            base_current=self.config["base_current"],
            load=self.state.load_factor,
            bearing_health=self.state.bearing_health,
            k_current=self.config["k_current"]
        )

        rpm = phys.compute_rpm(
            nominal_rpm=self.config["nominal_rpm"],
            misalignment=self.state.misalignment
        )

        # -------------------------
        # 4. Sensor drift (bias)
        # -------------------------
        self.sensor_bias["temperature"] += self.config["temp_drift"]
        self.sensor_bias["vibration"] += self.config["vibration_drift"]

        temperature = self.temperature + self.sensor_bias["temperature"]
        vibration = vibration + self.sensor_bias["vibration"]

        # -------------------------
        # 5. Gaussian noise
        # -------------------------
        temperature = add_gaussian_noise(temperature, self.config["noise_temperature"])
        vibration = add_gaussian_noise(vibration, self.config["noise_vibration"])
        current = add_gaussian_noise(current, self.config["noise_current"])
        rpm = add_gaussian_noise(rpm, self.config["noise_rpm"])

        # -------------------------
        # 6. Spikes (only vibration)
        # -------------------------
        vibration = add_spike(
            vibration,
            probability=self.config["spike_prob"],
            spike_magnitude=self.config["vibration_spike"]
        )

        # -------------------------
        # 7. Missing data
        # -------------------------
        temperature = maybe_drop(temperature, self.config["drop_prob"])
        vibration = maybe_drop(vibration, self.config["drop_prob"])
        current = maybe_drop(current, self.config["drop_prob"])
        rpm = maybe_drop(rpm, self.config["drop_prob"])

        return {
            "temperature": temperature,
            "vibration": vibration,
            "current": current,
            "rpm": rpm,
            "bearing_health": self.state.bearing_health
        }
