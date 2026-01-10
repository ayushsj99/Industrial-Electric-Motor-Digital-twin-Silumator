from simulator.state import MotorHiddenState
import simulator.physics as phys
from simulator.noise import add_gaussian_noise, add_spike, maybe_drop
from simulator.sensor_imperfections import SensorImperfectionSimulator
from collections import deque


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
        
        # -------------------------------
        # Phase 6: Asynchronous Response
        # -------------------------------
        # Health history buffer for sensor lag simulation
        # Different sensors "see" different time windows
        max_window = 30  # Keep last 30 timesteps
        self.health_history = deque([state.motor_health], maxlen=max_window)
        
        # Sensor-specific window sizes (in timesteps)
        self.sensor_windows = {
            "vibration": 1,    # Immediate response
            "current": 5,      # Short lag
            "temperature": 20  # Long lag
        }
        
        # -------------------------------
        # Phase 6: Sensor Imperfections
        # -------------------------------
        self.sensor_imperfections = SensorImperfectionSimulator(
            enable_imperfections=config.get("enable_sensor_imperfections", True)
        )
        
        # -------------------------------
        # Phase 6: Asynchronous Response
        # -------------------------------
        # Health history buffer for sensor lag simulation
        # Different sensors "see" different time windows
        max_window = 30  # Keep last 30 timesteps
        self.health_history = deque([state.motor_health], maxlen=max_window)
        
        # Sensor-specific window sizes (in timesteps)
        self.sensor_windows = {
            "vibration": 1,    # Immediate response
            "current": 5,      # Short lag
            "temperature": 20  # Long lag
        }
    
    def get_effective_health(self, sensor_type: str) -> float:
        """
        Get the effective health value as perceived by a specific sensor.
        Different sensors respond at different speeds.
        
        Args:
            sensor_type: One of 'vibration', 'current', 'temperature'
        
        Returns:
            Averaged health over the sensor's time window
        """
        window = self.sensor_windows.get(sensor_type, 1)
        
        # Take mean over the last 'window' timesteps
        recent_health = list(self.health_history)[-window:]
        return sum(recent_health) / len(recent_health)

    def step(self):
        """
        Advance the motor by one timestep (5 minutes of operation).
        """
        
        # Update operating hours (5 minutes = 1/12 hour)
        time_step_hours = self.config.get("time_step_minutes", 5) / 60.0
        self.state.hours_since_maintenance += time_step_hours

        # -------------------------
        # 1. Update degradation stage and hidden health
        # -------------------------
        # First, determine current degradation stage
        self.state.degradation_stage = phys.determine_degradation_stage(
            hours_since_maintenance=self.state.hours_since_maintenance,
            stage_0_duration=self.state.stage_0_duration_hours,
            stage_1_duration=self.state.stage_1_duration_hours,
            stage_2_duration=self.state.stage_2_duration_hours
        )
        
        # Update health using three-stage model
        self.state.motor_health = phys.update_motor_health(
            self.state.motor_health,
            self.state.hours_since_maintenance,
            self.state.degradation_stage,
            self.state.stage_0_duration_hours,
            self.state.stage_1_duration_hours,
            self.state.stage_2_duration_hours,
            self.state.stage_1_power_exponent,
            self.state.stage_2_exp_coefficient,
            self.config
        )
        
        # Update categorical health state
        self.state.health_state = phys.determine_health_state(
            self.state.motor_health,
            healthy_threshold=self.config.get("healthy_threshold", 0.7),
            warning_threshold=self.config.get("warning_threshold", 0.4)
        )
        
        # Add current health to history buffer
        self.health_history.append(self.state.motor_health)

        self.state.friction_coeff = phys.update_friction(
            base_friction=self.config["base_friction"],
            motor_health=self.state.motor_health,
            k_friction=self.config["k_friction"]
        )

        # -------------------------
        # 2. Update temperature (instantaneous reading)
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
        # 3. Sensor readings
        # -------------------------
        # Vibration: 20-second aggregated reading (RMS of multiple samples)
        vibration_health = self.get_effective_health("vibration")
        vibration_duration = self.config.get("vibration_sample_duration", 20)
        vibration_rate = self.config.get("vibration_sample_rate", 10)
        
        vibration = phys.compute_vibration(
            motor_health=vibration_health,
            misalignment=self.state.misalignment,
            v_base=self.config["v_base"],
            k_health=self.config["k_v_health"],
            k_align=self.config["k_v_align"],
            duration=vibration_duration,
            sample_rate=vibration_rate
        )

        # Current: short lag (5-step average)
        current_health = self.get_effective_health("current")
        current = phys.compute_current(
            base_current=self.config["base_current"],
            load=self.state.load_factor,
            motor_health=current_health,
            k_current=self.config["k_current"]
        )
        
        # Temperature: long lag (uses filtered health implicitly via friction)
        # Temperature is already lagged via thermal dynamics

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
        
        # -------------------------
        # 8. Sensor Imperfections (Phase 6)
        # -------------------------
        # Update sensor imperfection states
        self.sensor_imperfections.update()
        
        # Apply sensor-specific failures
        temperature = self.sensor_imperfections.apply_imperfections("temperature", temperature)
        vibration = self.sensor_imperfections.apply_imperfections("vibration", vibration)
        current = self.sensor_imperfections.apply_imperfections("current", current)
        rpm = self.sensor_imperfections.apply_imperfections("rpm", rpm)

        return {
            "temperature": temperature,
            "vibration": vibration,
            "current": current,
            "rpm": rpm,
            "motor_health": self.state.motor_health,
            "health_state": self.state.health_state.value,
            "hours_since_maintenance": self.state.hours_since_maintenance,
            "degradation_stage": self.state.degradation_stage.value
        }
