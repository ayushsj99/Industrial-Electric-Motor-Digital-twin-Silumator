"""
Instantaneous Mode Strategy - Automatic dataset generation with multiple cycles
"""
import pandas as pd
import numpy as np
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from .base_strategy import SimulationStrategy
from simulator.factory import FactorySimulator
from simulator.config_realistic import REALISTIC_CONFIG
from simulator.state import HealthState, DegradationStage


class InstantaneousStrategy(SimulationStrategy):
    """Strategy for instantaneous/batch simulation mode"""
    
    def initialize_factory(self, config) -> FactorySimulator:
        """Initialize factory for instantaneous mode - enable automatic maintenance"""
        modified_config = REALISTIC_CONFIG.copy()
        modified_config["noise_scale"] = config.noise_level
        # Pass UI thresholds to motor configuration
        modified_config["warning_threshold"] = config.warning_threshold
        modified_config["critical_threshold"] = config.critical_threshold
        
        factory = FactorySimulator(
            num_motors=config.num_motors,
            base_config=modified_config,
            enable_maintenance=True  # Enable auto maintenance in instantaneous mode
        )
        
        # Apply load factor AND degradation speed in instantaneous mode
        for motor in factory.motors:
            motor.state.load_factor *= config.load_factor
            # Apply degradation speed scaling (default 1.0)
            if hasattr(config, 'degradation_speed'):
                # Scale stage durations inversely (higher speed = shorter duration)
                speed_factor = 1.0 / config.degradation_speed
                motor.state.stage_0_duration_hours *= speed_factor
                motor.state.stage_1_duration_hours *= speed_factor
                motor.state.stage_2_duration_hours *= speed_factor
                motor.state.target_hours_to_critical *= speed_factor
        
        return factory
    
    def step(self, num_steps: int = 1) -> pd.DataFrame:
        """Instantaneous mode step - no pausing, all motors run continuously"""
        if self.manager.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        new_records = []
        
        for _ in range(num_steps):
            step_records = self.manager.factory.step()
            
            # No filtering in instantaneous mode - all motors run continuously
            for record in step_records:
                record["time"] = self.manager.current_time
                # Add cycle_id if not present (for backward compatibility)
                if "cycle_id" not in record:
                    record["cycle_id"] = 0  # Default cycle for legacy mode
                new_records.append(record)
            
            self.manager.current_time += 1
        
        # Add to history
        self.manager.history.extend(new_records)
        
        # For instantaneous mode, be more generous with history limits
        max_allowed = self.manager.config.max_history
        if len(self.manager.history) > max_allowed:
            excess = len(self.manager.history) - max_allowed
            self.manager.history = self.manager.history[excess:]
        
        return pd.DataFrame(new_records)
    
    def handle_critical_motor(self, motor_id: int, health: float) -> bool:
        """In instantaneous mode, never pause motors - let automatic maintenance handle it"""
        return True  # Always continue
    
    def should_perform_maintenance(self, motor_id: int) -> bool:
        """Maintenance is handled automatically by factory in instantaneous mode"""
        return False  # Manager doesn't perform maintenance in this mode
    
    def reset_motor(self, motor_id: int):
        """Use factory's automatic maintenance for proper reset"""
        if self.manager.factory is None:
            raise ValueError("Factory not initialized")
        
        for motor in self.manager.factory.motors:
            if motor.motor_id == motor_id:
                # Use factory's proven automatic maintenance logic
                self.manager.factory._perform_automatic_maintenance(motor)
                # Update manager tracking
                self.manager.last_maintenance_time[motor_id] = self.manager.current_time
                break
    
    def generate_until_all_critical(self, max_steps: int = 100000) -> pd.DataFrame:
        """
        Generate data with proper motor/cycle structure.
        Each motor goes through specified number of complete maintenance cycles.
        """
        if self.manager.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        all_records = []
        total_motors = self.manager.config.num_motors
        target_cycles = self.manager.config.target_maintenance_cycles
        
        print(f"Starting structured data generation: {total_motors} motors, {target_cycles} cycle(s) each")
        
        # Proper multi-level loop structure: Motor -> Cycles -> Timesteps
        for motor in self.manager.factory.motors:
            motor_id = motor.motor_id
            print(f"\nProcessing Motor {motor_id}:")
            
            for cycle_num in range(target_cycles):
                print(f"  Cycle {cycle_num + 1}/{target_cycles}")
                cycle_records = []
                cycle_start_time = self.manager.current_time
                
                # Reset health for new cycle (preserve motor identity)
                self._reset_health_only(motor)
                
                # Generate complete lifecycle for this motor/cycle
                steps_in_cycle = 0
                max_cycle_steps = 50000  # Safety limit per cycle to prevent infinite loops
                
                while (motor.state.health_state != HealthState.CRITICAL and 
                       steps_in_cycle < max_cycle_steps):
                    
                    # Step motor simulation
                    sensors = motor.step()
                    
                    # Add metadata
                    sensors.update({
                        'motor_id': motor_id,
                        'cycle_id': cycle_num,
                        'time': self.manager.current_time,
                        'regime': getattr(self.manager.factory, 'current_regime', 'normal'),
                        'maintenance_event': None  # No maintenance during normal operation
                    })
                    
                    cycle_records.append(sensors)
                    self.manager.current_time += 1
                    steps_in_cycle += 1
                
                # Trigger maintenance at end of cycle
                if motor.state.health_state == HealthState.CRITICAL:
                    # Perform maintenance
                    self.manager.factory._perform_automatic_maintenance(motor)
                    
                    # Add maintenance event record
                    maintenance_sensors = motor.step()
                    maintenance_sensors.update({
                        'motor_id': motor_id,
                        'cycle_id': cycle_num,
                        'time': self.manager.current_time,
                        'regime': getattr(self.manager.factory, 'current_regime', 'normal'),
                        'maintenance_event': 'automatic_maintenance'
                    })
                    cycle_records.append(maintenance_sensors)
                    self.manager.current_time += 1
                    
                    print(f"    Completed cycle {cycle_num + 1}: {len(cycle_records)} timesteps")
                else:
                    # Force critical state if motor didn't reach it naturally
                    print(f"    Warning: Motor {motor_id} cycle {cycle_num + 1} hit step limit ({steps_in_cycle} steps)")
                    print(f"    Current health: {motor.state.motor_health:.3f}, state: {motor.state.health_state}")
                    print(f"    Forcing critical state and maintenance...")
                    
                    # Force critical state
                    motor.state.health_state = HealthState.CRITICAL
                    motor.state.motor_health = 0.1  # Force low health
                    
                    # Perform forced maintenance
                    self.manager.factory._perform_automatic_maintenance(motor)
                    
                    # Add forced maintenance event
                    forced_sensors = motor.step()
                    forced_sensors.update({
                        'motor_id': motor_id,
                        'cycle_id': cycle_num,
                        'time': self.manager.current_time,
                        'regime': getattr(self.manager.factory, 'current_regime', 'normal'),
                        'maintenance_event': 'forced_maintenance_timeout'
                    })
                    cycle_records.append(forced_sensors)
                    self.manager.current_time += 1
                    
                    print(f"    Forced completion of cycle {cycle_num + 1}: {len(cycle_records)} timesteps")
                
                all_records.extend(cycle_records)
        
        print(f"\n✓ Structured generation complete: {len(all_records)} total records")
        print(f"  {total_motors} motors × {target_cycles} cycles each")
        
        # Store generated data in manager history for verification and export
        self.manager.history.extend(all_records)
        
        # For instantaneous mode, don't trim history during generation
        # The complete dataset is needed for verification and export
        print(f"✓ Data stored in history: {len(self.manager.history)} total records")
        print(f"📊 Dataset ready for verification and export!")
        
        return pd.DataFrame(all_records)
    
    def _reset_health_only(self, motor):
        """
        Reset only health-related state for new cycle, preserve motor identity.
        
        Args:
            motor: Motor instance to reset
        """
        # Probabilistic recovery (80-98% range) - already handled in factory maintenance
        # But we need to reset for cycle start
        recovery_factor = np.random.uniform(0.85, 0.98)  # Slightly better for cycle start
        motor.state.motor_health = recovery_factor
        motor.state.hours_since_maintenance = 0.0
        motor.state.health_state = HealthState.HEALTHY
        motor.state.degradation_stage = DegradationStage.STAGE_0_HEALTHY
        
        # Update health history for lag simulation
        if hasattr(motor, 'health_history'):
            motor.health_history.clear()
            motor.health_history.append(motor.state.motor_health)