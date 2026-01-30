"""
Live Mode Strategy - Interactive simulation with user decisions
"""
import pandas as pd
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from .base_strategy import SimulationStrategy
from simulator.factory import FactorySimulator
from simulator.config_realistic import REALISTIC_CONFIG


class LiveModeStrategy(SimulationStrategy):
    """Strategy for live/interactive simulation mode"""
    
    def initialize_factory(self, config) -> FactorySimulator:
        """Initialize factory for live mode - disable automatic maintenance"""
        modified_config = REALISTIC_CONFIG.copy()
        modified_config["noise_scale"] = config.noise_level
        # Pass UI thresholds to motor configuration
        modified_config["warning_threshold"] = config.warning_threshold
        modified_config["critical_threshold"] = config.critical_threshold
        
        factory = FactorySimulator(
            num_motors=config.num_motors,
            base_config=modified_config,
            enable_maintenance=False  # Disable auto maintenance in live mode
        )
        
        # Apply load factor and degradation speed scaling for live mode
        for motor in factory.motors:
            motor.state.load_factor *= config.load_factor
            # Scale stage durations for faster degradation in live mode
            if config.degradation_speed != 1.0:
                speed_factor = 1.0 / config.degradation_speed
                motor.state.stage_0_duration_hours *= speed_factor
                motor.state.stage_1_duration_hours *= speed_factor
                motor.state.stage_2_duration_hours *= speed_factor
                motor.state.target_hours_to_critical *= speed_factor
        
        return factory
    
    def step(self, num_steps: int = 1) -> pd.DataFrame:
        """Live mode step with user interaction and pausing"""
        if self.manager.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        new_records = []
        
        for _ in range(num_steps):
            step_records = self.manager.factory.step()
            
            # Filter out paused and failed motors from data generation
            active_records = []
            for record in step_records:
                motor_id = record["motor_id"]
                
                # Skip if motor is failed
                if motor_id in self.manager.failed_motors:
                    continue
                
                # Skip if motor is paused (waiting for user decision)
                if motor_id in self.manager.paused_motors:
                    continue
                
                # Check for critical health BEFORE adding to records
                health = record.get("motor_health", 1.0)
                if health <= self.manager.alert_threshold and motor_id not in self.manager.pending_decisions:
                    # Pause this motor and add to pending decisions
                    self.manager._pause_motor_for_decision(motor_id, health)
                    # Skip this record since motor is now paused
                    continue
                
                record["time"] = self.manager.current_time
                active_records.append(record)
            
            new_records.extend(active_records)
            self.manager.current_time += 1
            
            # Check for manual maintenance cycles in live mode
            if self.manager.config.auto_maintenance_enabled:
                self._check_and_perform_auto_maintenance()
        
        # Add to history
        self.manager.history.extend(new_records)
        
        # Trim history if too large
        if len(self.manager.history) > self.manager.config.max_history * self.manager.config.num_motors:
            excess = len(self.manager.history) - self.manager.config.max_history * self.manager.config.num_motors
            self.manager.history = self.manager.history[excess:]
        
        return pd.DataFrame(new_records)
    
    def handle_critical_motor(self, motor_id: int, health: float) -> bool:
        """Pause motor and request user decision"""
        if motor_id not in self.manager.pending_decisions:
            self.manager._pause_motor_for_decision(motor_id, health)
            return False  # Motor is paused
        return True
    
    def should_perform_maintenance(self, motor_id: int) -> bool:
        """Check if manual maintenance should be performed"""
        last_maintenance = self.manager.last_maintenance_time.get(motor_id, 0)
        time_since_maintenance = self.manager.current_time - last_maintenance
        return time_since_maintenance >= self.manager.config.maintenance_cycle_period
    
    def reset_motor(self, motor_id: int):
        """Reset motor with manual maintenance logic"""
        if self.manager.factory is None:
            raise ValueError("Factory not initialized")
        
        for motor in self.manager.factory.motors:
            if motor.motor_id == motor_id:
                # Simple reset for live mode (user-controlled)
                motor.state.motor_health = 1.0
                motor.state.misalignment = 0.05
                motor.state.friction_coeff = REALISTIC_CONFIG["base_friction"]
                # Update last maintenance time
                self.manager.last_maintenance_time[motor_id] = self.manager.current_time
                break
    
    def _check_and_perform_auto_maintenance(self):
        """Check for time-based maintenance cycles in live mode"""
        if self.manager.factory is None:
            return
        
        for motor in self.manager.factory.motors:
            motor_id = motor.motor_id
            if self.should_perform_maintenance(motor_id):
                self.reset_motor(motor_id)