"""
Instantaneous Mode Strategy - Automatic dataset generation with multiple cycles
"""
import pandas as pd
import numpy as np
import sys
import os
import gc
import psutil
from typing import List, Dict, Optional

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
    
    def _get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        try:
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024
        except:
            return 0.0
    
    def _estimate_record_size(self, record: Dict) -> int:
        """Estimate memory size of a record in bytes"""
        # Rough estimate: ~500 bytes per record (12 fields × ~40 bytes each)
        return 500
    
    def _check_memory_limits(self, current_records: int, estimated_total: int) -> bool:
        """Check if we're approaching memory limits"""
        current_mb = self._get_memory_usage_mb()
        
        # Conservative limits for Hugging Face Spaces (assume 14GB limit with 2GB buffer)
        max_memory_mb = 12000  # 12GB limit
        max_records = 2000000   # ~2M records max
        
        memory_ok = current_mb < max_memory_mb
        records_ok = current_records < max_records
        
        if not memory_ok:
            print(f"⚠️ Memory usage high: {current_mb:.1f}MB / {max_memory_mb}MB")
        if not records_ok:
            print(f"⚠️ Record count high: {current_records} / {max_records}")
            
        return memory_ok and records_ok
    
    def _process_batch(self, batch_records: List[Dict], batch_size: int = 50000) -> None:
        """Process a batch of records and manage memory"""
        if len(batch_records) >= batch_size:
            # Add to manager history in chunks
            self.manager.history.extend(batch_records)
            
            # Force garbage collection to free memory
            gc.collect()
            
            # Clear the batch
            batch_records.clear()
            
            print(f"  📦 Processed batch: {len(self.manager.history)} total records, {self._get_memory_usage_mb():.1f}MB")
    
    def _estimate_record_size(self, record: Dict) -> int:
        """Estimate memory size of a record in bytes"""
        # Rough estimate: ~500 bytes per record (12 fields × ~40 bytes each)
        return 500
    
    def _check_memory_limits(self, current_records: int, estimated_total: int) -> bool:
        """Check if we're approaching memory limits"""
        current_mb = self._get_memory_usage_mb()
        
        # Conservative limits for Hugging Face Spaces (assume 14GB limit with 2GB buffer)
        max_memory_mb = 12000  # 12GB limit
        max_records = 2000000   # ~2M records max
        
        memory_ok = current_mb < max_memory_mb
        records_ok = current_records < max_records
        
        if not memory_ok:
            print(f"⚠️ Memory usage high: {current_mb:.1f}MB / {max_memory_mb}MB")
        if not records_ok:
            print(f"⚠️ Record count high: {current_records} / {max_records}")
            
        return memory_ok and records_ok
    
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
        Memory-efficient data generation with global timeline synchronization.
        Uses batching and memory monitoring to prevent crashes on large datasets.
        """
        if self.manager.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        total_motors = self.manager.config.num_motors
        target_cycles = self.manager.config.target_maintenance_cycles
        
        # Estimate dataset size and check feasibility
        estimated_records_per_cycle = 15000  # Conservative estimate
        estimated_total_records = total_motors * target_cycles * estimated_records_per_cycle
        
        print(f"Starting synchronized data generation: {total_motors} motors, {target_cycles} cycle(s) each")
        print(f"Estimated dataset size: ~{estimated_total_records:,} records")
        
        # Memory-safe limits check
        if estimated_total_records > 3000000:  # 3M records limit
            print(f"⚠️ WARNING: Large dataset detected ({estimated_total_records:,} records)")
            print(f"⚠️ This may cause memory issues on Hugging Face Spaces.")
            print(f"💡 Consider reducing motors ({total_motors}) or cycles ({target_cycles}) for stability.")
            print(f"📊 Proceeding with memory-efficient generation...\n")
        
        print("All motors operate on shared global timeline")
        
        # Reset global time to 0 for synchronized start
        self.manager.current_time = 0
        self.manager.history = []  # Clear existing history
        
        # Track cycles completed per motor
        motor_cycles_completed = {motor.motor_id: 0 for motor in self.manager.factory.motors}
        motor_completed = {motor.motor_id: False for motor in self.manager.factory.motors}
        
        # Reset all motors to start fresh on global timeline
        for motor in self.manager.factory.motors:
            self._reset_health_only(motor)
        
        # Batch processing for memory efficiency
        batch_records = []
        batch_size = 25000  # Process in 25K record batches
        global_timestep = 0
        
        print("\nGlobal timeline simulation starting...")
        
        # Main simulation loop with memory management
        while (not all(motor_completed.values()) and global_timestep < max_steps):
            timestep_records = []
            
            # Memory check every 5000 steps
            if global_timestep % 5000 == 0 and global_timestep > 0:
                if not self._check_memory_limits(len(self.manager.history), estimated_total_records):
                    print(f"\n⚠️ Memory limits reached at step {global_timestep}")
                    print(f"📊 Stopping generation with {len(self.manager.history)} records")
                    break
            
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
            
            # Add timestep records to batch
            batch_records.extend(timestep_records)
            
            # Process batch if it's large enough
            self._process_batch(batch_records, batch_size)
            
            # Advance global time
            self.manager.current_time += 1
            global_timestep += 1
            
            # Progress reporting every 10000 steps
            if global_timestep % 10000 == 0:
                active_motors = sum(1 for completed in motor_completed.values() if not completed)
                print(f"  Global time {self.manager.current_time}: {active_motors} motors still active")
        
        # Process any remaining batch records
        if batch_records:
            self.manager.history.extend(batch_records)
            batch_records.clear()
        
        # Handle motors that didn't complete naturally (simplified for memory efficiency)
        incomplete_motors = [motor_id for motor_id, completed in motor_completed.items() if not completed]
        if incomplete_motors:
            print(f"  Note: {len(incomplete_motors)} motors didn't complete all cycles within time limit")
        
        # Final cleanup
        gc.collect()
        
        total_records = len(self.manager.history)
        final_memory = self._get_memory_usage_mb()
        
        print(f"\n✓ Synchronized generation complete: {total_records:,} total records")
        print(f"  {total_motors} motors × {target_cycles} cycles each")
        print(f"  Global timeline: 0 to {self.manager.current_time} timesteps")
        print(f"  Memory usage: {final_memory:.1f}MB")
        print(f"✓ Data stored in history: {total_records:,} total records")
        print("📊 Dataset ready for verification and export!")
        
        # Return DataFrame for immediate use (more memory efficient than storing twice)
        if total_records > 1000000:  # 1M+ records
            print(f"💡 Large dataset - consider downloading in chunks if needed")
            
        return pd.DataFrame(self.manager.history)
    
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