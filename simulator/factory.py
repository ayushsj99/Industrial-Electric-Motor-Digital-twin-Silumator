import copy
import numpy as np
from simulator.motor import Motor
from simulator.state import MotorHiddenState, HealthState, DegradationStage
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
        
        # Track automatic maintenance scheduling
        # Key: motor_id, Value: scheduled timestep for maintenance
        self.scheduled_automatic_maintenance = {}
        # Track previous health state to detect entry into critical
        self.previous_health_states = {}

        for motor_id in range(num_motors):
            motor = self._create_motor(motor_id, base_config)
            self.motors.append(motor)

    def _create_motor(self, motor_id, base_config):
        """
        Create one motor with lognormal lifespan distribution and three-stage degradation.
        """
        config = copy.deepcopy(base_config)

        # ---- Motor personality (controlled variation) ----
        load_factor = 0.9 + 0.1 * motor_id          # increasing load
        misalignment = 0.02 * motor_id               # increasing misalignment

        # ---- Simple uniform lifespan distribution (1000-3000 hours) ----
        min_hours = config.get("min_hours_to_critical", 1000)
        max_hours = config.get("max_hours_to_critical", 3000)
        total_lifespan_hours = np.random.uniform(min_hours, max_hours)
        
        # ---- Three-stage duration allocation ----
        # Stage 0: 70-85% of life
        stage_0_pct = np.random.uniform(
            config.get("stage_0_min_pct", 0.70),
            config.get("stage_0_max_pct", 0.85)
        )
        
        # Stage 1: 12-22% of life
        stage_1_pct = np.random.uniform(
            config.get("stage_1_min_pct", 0.12),
            config.get("stage_1_max_pct", 0.22)
        )
        
        # Stage 2: Remaining (typically 5-10%)
        stage_2_pct = 1.0 - stage_0_pct - stage_1_pct
        
        # Calculate stage durations in hours
        stage_0_duration = total_lifespan_hours * stage_0_pct
        stage_1_duration = total_lifespan_hours * stage_1_pct
        stage_2_duration = total_lifespan_hours * stage_2_pct
        
        # ---- Stage-specific parameters ----
        # Power law exponent for stage 1: b ∈ [1.5, 3.5]
        stage_1_power_exp = np.random.uniform(
            config.get("stage_1_power_exp_min", 1.5),
            config.get("stage_1_power_exp_max", 3.5)
        )
        
        # Exponential coefficient for stage 2 (calculated in physics)
        stage_2_exp_coeff = 0.0  # Placeholder, calculated dynamically
        
        state = MotorHiddenState(
            motor_health=config.get("stage_0_base_health", 0.95),
            health_state=HealthState.HEALTHY,
            degradation_stage=DegradationStage.STAGE_0_HEALTHY,
            load_factor=load_factor,
            misalignment=misalignment,
            friction_coeff=config["base_friction"],
            hours_since_maintenance=0.0,
            target_hours_to_critical=total_lifespan_hours,
            stage_0_duration_hours=stage_0_duration,
            stage_1_duration_hours=stage_1_duration,
            stage_2_duration_hours=stage_2_duration,
            stage_1_power_exponent=stage_1_power_exp,
            stage_2_exp_coefficient=stage_2_exp_coeff
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
            # Track entry into critical state and schedule maintenance
            # -------------------------------
            motor_id = motor.motor_id
            prev_state = self.previous_health_states.get(motor_id)
            current_state = motor.state.health_state
            
            # Detect transition into critical state
            if (prev_state != HealthState.CRITICAL and 
                current_state == HealthState.CRITICAL and 
                motor_id not in self.scheduled_automatic_maintenance):
                # Schedule maintenance randomly within 1 day (24 hours = 288 timesteps)
                delay = np.random.randint(1, 289)  # 1 to 288 timesteps (5 min to 24 hours)
                self.scheduled_automatic_maintenance[motor_id] = self.time + delay
            
            # Update previous state tracker
            self.previous_health_states[motor_id] = current_state
            
            # -------------------------------
            # Check for scheduled automatic maintenance
            # -------------------------------
            automatic_maintenance_occurred = False
            if (motor_id in self.scheduled_automatic_maintenance and 
                self.time >= self.scheduled_automatic_maintenance[motor_id] and
                motor.state.motor_health < 0.30):  # Only if health < 30%
                # Perform automatic maintenance
                self._perform_automatic_maintenance(motor)
                automatic_maintenance_occurred = True
                # Remove from schedule
                del self.scheduled_automatic_maintenance[motor_id]
            
            # -------------------------------
            # Check for scheduled maintenance
            # -------------------------------
            maintenance_type = self.maintenance_scheduler.should_perform_maintenance(
                timestep=self.time,
                motor_id=motor.motor_id,
                motor_health=motor.state.motor_health
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
            
            # Label maintenance events (prioritize automatic over scheduled)
            if automatic_maintenance_occurred:
                sensors["maintenance_event"] = "automatic_maintenance"
            else:
                sensors["maintenance_event"] = maintenance_type
            
            records.append(sensors)

        self.time += 1
        return records
    
    def _perform_automatic_maintenance(self, motor):
        """
        Perform automatic maintenance when motor reaches critical state.
        Resets motor to new lifecycle with fresh lognormal lifespan.
        
        Args:
            motor: Motor instance to maintain
        """
        # Reset health to good condition
        base_health = motor.config.get("stage_0_base_health", 0.95)
        motor.state.motor_health = np.random.uniform(base_health - 0.02, base_health)
        motor.state.health_state = HealthState.HEALTHY
        motor.state.degradation_stage = DegradationStage.STAGE_0_HEALTHY
        
        # Reset operating hours counter
        motor.state.hours_since_maintenance = 0.0
        
        # ---- Generate new random lifespan (1000-3000 hours) ----
        min_hours = motor.config.get("min_hours_to_critical", 1000)
        max_hours = motor.config.get("max_hours_to_critical", 3000)
        total_lifespan_hours = np.random.uniform(min_hours, max_hours)
        motor.state.target_hours_to_critical = total_lifespan_hours
        
        # ---- Regenerate three-stage durations ----
        stage_0_pct = np.random.uniform(
            motor.config.get("stage_0_min_pct", 0.70),
            motor.config.get("stage_0_max_pct", 0.85)
        )
        stage_1_pct = np.random.uniform(
            motor.config.get("stage_1_min_pct", 0.12),
            motor.config.get("stage_1_max_pct", 0.22)
        )
        
        motor.state.stage_0_duration_hours = total_lifespan_hours * stage_0_pct
        motor.state.stage_1_duration_hours = total_lifespan_hours * stage_1_pct
        motor.state.stage_2_duration_hours = total_lifespan_hours * (1.0 - stage_0_pct - stage_1_pct)
        
        # Regenerate stage-specific parameters
        motor.state.stage_1_power_exponent = np.random.uniform(
            motor.config.get("stage_1_power_exp_min", 1.5),
            motor.config.get("stage_1_power_exp_max", 3.5)
        )
        motor.state.stage_2_exp_coefficient = 0.0
        
        # Partially reset other factors
        motor.state.misalignment *= 0.3
        motor.state.friction_coeff = motor.config["base_friction"] * 1.1
