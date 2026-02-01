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
        Generate data with global timeline where all motors operate simultaneously.
        Each motor goes through specified number of complete maintenance cycles.
        All motors start at time 0 and advance together through global factory time.
        """
        if self.manager.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        all_records = []
        total_motors = self.manager.config.num_motors
        target_cycles = self.manager.config.target_maintenance_cycles
        
        print(f"Starting synchronized data generation: {total_motors} motors, {target_cycles} cycle(s) each")
        print("All motors operate on shared global timeline")
        
        # Reset global time to 0 for synchronized start
        self.manager.current_time = 0
        
        # Track cycles completed per motor
        motor_cycles_completed = {motor.motor_id: 0 for motor in self.manager.factory.motors}
        motor_completed = {motor.motor_id: False for motor in self.manager.factory.motors}
        
        # Reset all motors to start fresh on global timeline
        for motor in self.manager.factory.motors:
            self._reset_health_only(motor)
        
        # Global time simulation - all motors advance together
        global_timestep = 0
        max_global_steps = max_steps  # Overall safety limit
        
        print(f"\nGlobal timeline simulation starting...")
        
        while (not all(motor_completed.values()) and global_timestep < max_global_steps):
            timestep_records = []
            
            # Advance ALL motors simultaneously for this timestep
            for motor in self.manager.factory.motors:
                motor_id = motor.motor_id
                
                # Skip motors that have completed all their cycles
                if motor_completed[motor_id]:
                    continue
                
                # Step this motor's simulation
                sensors = motor.step()
                
                # Check if motor reached critical state (end of cycle)
                if motor.state.health_state == HealthState.CRITICAL:
                    # Complete this cycle
                    motor_cycles_completed[motor_id] += 1
                    current_cycle = motor_cycles_completed[motor_id] - 1
                    
                    # Add critical state record
                    sensors.update({
                        'motor_id': motor_id,
                        'cycle_id': current_cycle,
                        'time': self.manager.current_time,
                        'regime': getattr(self.manager.factory, 'current_regime', 'normal'),
                        'maintenance_event': None
                    })
                    timestep_records.append(sensors)
                    
                    # Perform maintenance and add maintenance record
                    self.manager.factory._perform_automatic_maintenance(motor)
                    
                    # Generate post-maintenance sensor reading
                    maintenance_sensors = motor.step()
                    maintenance_sensors.update({
                        'motor_id': motor_id,
                        'cycle_id': current_cycle,
                        'time': self.manager.current_time + 0.5,  # Half-step for maintenance
                        'regime': getattr(self.manager.factory, 'current_regime', 'normal'),
                        'maintenance_event': 'automatic_maintenance'
                    })
                    timestep_records.append(maintenance_sensors)
                    
                    # Check if motor completed all required cycles
                    if motor_cycles_completed[motor_id] >= target_cycles:
                        motor_completed[motor_id] = True
                        print(f"  Motor {motor_id}: Completed all {target_cycles} cycles at time {self.manager.current_time}")
                    else:
                        # Reset for next cycle
                        self._reset_health_only(motor)
                        print(f"  Motor {motor_id}: Completed cycle {motor_cycles_completed[motor_id]}/{target_cycles}")
                else:
                    # Normal operation record
                    current_cycle = motor_cycles_completed[motor_id]
                    sensors.update({
                        'motor_id': motor_id,
                        'cycle_id': current_cycle,
                        'time': self.manager.current_time,
                        'regime': getattr(self.manager.factory, 'current_regime', 'normal'),
                        'maintenance_event': None
                    })
                    timestep_records.append(sensors)
            
            # Add all timestep records to history
            all_records.extend(timestep_records)
            
            # Advance global time
            self.manager.current_time += 1
            global_timestep += 1
            
            # Progress reporting every 10000 steps
            if global_timestep % 10000 == 0:
                active_motors = sum(1 for completed in motor_completed.values() if not completed)
                print(f"  Global time {self.manager.current_time}: {active_motors} motors still active")
        
        # Handle motors that didn't complete naturally
        for motor_id, completed in motor_completed.items():
            if not completed:
                remaining_cycles = target_cycles - motor_cycles_completed[motor_id]
                print(f"  Warning: Motor {motor_id} did not complete {remaining_cycles} cycles naturally")
                
                # Force completion for data consistency
                motor = next(m for m in self.manager.factory.motors if m.motor_id == motor_id)
                for cycle in range(remaining_cycles):
                    # Force critical state and maintenance
                    motor.state.health_state = HealthState.CRITICAL
                    motor.state.motor_health = 0.1
                    
                    # Add forced completion records
                    sensors = motor.step()
                    current_cycle = motor_cycles_completed[motor_id] + cycle
                    sensors.update({
                        'motor_id': motor_id,
                        'cycle_id': current_cycle,
                        'time': self.manager.current_time + cycle,
                        'regime': 'forced',
                        'maintenance_event': 'forced_completion'
                    })
                    all_records.append(sensors)
                    
                    # Perform maintenance
                    self.manager.factory._perform_automatic_maintenance(motor)
        
        print(f"\n✓ Synchronized generation complete: {len(all_records)} total records")
        print(f"  {total_motors} motors × {target_cycles} cycles each")
        print(f"  Global timeline: 0 to {self.manager.current_time} timesteps")
        
        # Store complete dataset in manager history
        self.manager.history = all_records
        print(f"✓ Data stored in history: {len(all_records)} total records")
        print("📊 Dataset ready for verification and export!")
        
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