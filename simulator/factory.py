import copy
import numpy as np
from simulator.motor import Motor
from simulator.state import MotorHiddenState
from simulator.config import DEFAULT_CONFIG
from simulator.maintenance import MaintenanceScheduler


class OperatingRegime:
    """Operating regime definitions for factory"""
    IDLE = "idle"
    NORMAL = "normal"
    PEAK = "peak"
    
    @staticmethod
    def get_regime_params(regime: str) -> dict:
        """
        Get parameter multipliers for each operating regime.
        
        Returns dict with:
        - load_multiplier: How much to scale motor load
        - noise_multiplier: How much to scale sensor noise
        - temp_multiplier: How much to scale temperature rise
        - degradation_multiplier: How much to scale wear
        """
        regimes = {
            OperatingRegime.IDLE: {
                "load_multiplier": 0.3,
                "noise_multiplier": 0.5,
                "temp_multiplier": 0.2,
                "degradation_multiplier": 0.5
            },
            OperatingRegime.NORMAL: {
                "load_multiplier": 1.0,
                "noise_multiplier": 1.0,
                "temp_multiplier": 1.0,
                "degradation_multiplier": 1.0
            },
            OperatingRegime.PEAK: {
                "load_multiplier": 1.5,
                "noise_multiplier": 1.4,
                "temp_multiplier": 1.8,
                "degradation_multiplier": 1.6
            }
        }
        return regimes.get(regime, regimes[OperatingRegime.NORMAL])


class FactorySimulator:
    def __init__(self, num_motors=5, base_config=DEFAULT_CONFIG, enable_regimes=True, enable_maintenance=True):
        self.time = 0
        self.motors = []
        self.base_config = base_config
        
        # -------------------------------
        # Phase 6: Operating Regimes
        # -------------------------------
        self.enable_regimes = enable_regimes
        self.current_regime = OperatingRegime.NORMAL
        self.regime_timer = 0
        self.regime_duration = 100  # How long each regime lasts
        
        # Regime transition probabilities
        self.regime_transitions = {
            OperatingRegime.IDLE: {
                OperatingRegime.IDLE: 0.7,
                OperatingRegime.NORMAL: 0.3,
                OperatingRegime.PEAK: 0.0
            },
            OperatingRegime.NORMAL: {
                OperatingRegime.IDLE: 0.1,
                OperatingRegime.NORMAL: 0.7,
                OperatingRegime.PEAK: 0.2
            },
            OperatingRegime.PEAK: {
                OperatingRegime.IDLE: 0.0,
                OperatingRegime.NORMAL: 0.8,
                OperatingRegime.PEAK: 0.2
            }
        }
        
        # -------------------------------
        # Phase 6: Maintenance Events
        # -------------------------------
        self.maintenance_scheduler = MaintenanceScheduler(enable_maintenance=enable_maintenance)

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

    def _select_next_regime(self) -> str:
        """
        Select next operating regime based on transition probabilities.
        """
        transitions = self.regime_transitions[self.current_regime]
        regimes = list(transitions.keys())
        probs = list(transitions.values())
        
        return np.random.choice(regimes, p=probs)
    
    def _apply_regime_effects(self, motor: Motor, regime_params: dict):
        """
        Temporarily modify motor parameters based on current regime.
        This modifies the motor's load factor dynamically.
        """
        # Temporarily scale load (will affect this step only)
        original_load = motor.state.load_factor
        motor.state.load_factor *= regime_params["load_multiplier"]
        
        return original_load

    def step(self):
        """
        Advance all motors by one timestep.
        """
        # -------------------------------
        # Update operating regime
        # -------------------------------
        if self.enable_regimes:
            self.regime_timer += 1
            
            # Check if it's time to transition
            if self.regime_timer >= self.regime_duration:
                self.current_regime = self._select_next_regime()
                self.regime_timer = 0
                # Randomize next duration (80-120% of base)
                self.regime_duration = int(100 * np.random.uniform(0.8, 1.2))
        
        # Get current regime parameters
        regime_params = OperatingRegime.get_regime_params(self.current_regime)
        
        # -------------------------------
        # Process each motor
        # -------------------------------
        records = []
        for motor in self.motors:
            # -------------------------------
            # Check for maintenance
            # -------------------------------
            maintenance_type = self.maintenance_scheduler.should_perform_maintenance(
                timestep=self.time,
                motor_id=motor.motor_id,
                bearing_health=motor.state.bearing_health
            )
            
            if maintenance_type:
                self.maintenance_scheduler.perform_maintenance(
                    motor=motor,
                    maintenance_type=maintenance_type,
                    timestep=self.time
                )
            
            # Apply regime effects
            if self.enable_regimes:
                original_load = self._apply_regime_effects(motor, regime_params)
            
            sensors = motor.step()
            
            # Restore original load
            if self.enable_regimes:
                motor.state.load_factor = original_load
            
            sensors["time"] = self.time
            sensors["motor_id"] = motor.motor_id
            sensors["regime"] = self.current_regime  # Add regime to output
            sensors["maintenance_event"] = maintenance_type  # Add maintenance flag
            records.append(sensors)

        self.time += 1
        return records
