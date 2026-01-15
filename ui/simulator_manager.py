"""
Simulator Manager - Handles persistent simulator state and lifecycle
"""
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
import time

import sys
import os
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from simulator.factory import FactorySimulator
from simulator.config_realistic import REALISTIC_CONFIG


@dataclass
class SimulatorConfig:
    """Configuration for the simulator"""
    num_motors: int = 5
    degradation_speed: float = 1.0
    noise_level: float = 1.0
    load_factor: float = 1.0
    max_history: int = 2000  # Maximum timesteps to keep (5-min intervals, ~7 days)
    auto_maintenance_enabled: bool = True  # Enable automatic maintenance at critical
    maintenance_cycle_period: int = 3600  # Hours between scheduled maintenance checks
    generation_mode: str = "live"  # "live" or "instantaneous"
    target_maintenance_cycles: int = 1  # Number of maintenance cycles to generate per motor



class SimulatorState:
    """Simulation states"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SimulatorManager:
    """
    Manages the lifecycle of the factory simulator with persistent state
    """
    
    def __init__(self):
        self.factory: Optional[FactorySimulator] = None
        self.history: List[Dict] = []
        self.current_time: int = 0
        self.config: SimulatorConfig = SimulatorConfig()
        self.state: str = SimulatorState.STOPPED
        self.alert_threshold: float = 0.3  # Health threshold for alerts
        self.last_maintenance_time: Dict[int, int] = {}  # Track last maintenance per motor
        self.paused_motors: Dict[int, Dict] = {}  # Motors waiting for user decision {motor_id: {reason, health, timestamp}}
        self.failed_motors: Dict[int, Dict] = {}  # Motors that have failed {motor_id: {timestamp, last_state}}
        self.pending_decisions: List[int] = []  # Motors waiting for user decision
        
    def initialize(self, config: SimulatorConfig):
        """Initialize or reinitialize the factory simulator"""
        self.config = config
        
        # Create modified config with user parameters
        modified_config = REALISTIC_CONFIG.copy()
        modified_config["noise_scale"] = config.noise_level
        
        self.factory = FactorySimulator(
            num_motors=config.num_motors,
            base_config=modified_config
        )
        
        # Apply load factor and degradation speed to all motors
        for motor in self.factory.motors:
            motor.state.load_factor *= config.load_factor
            motor.config["base_decay"] *= config.degradation_speed
        
        # Initialize maintenance tracking for all motors
        self.last_maintenance_time = {motor.motor_id: 0 for motor in self.factory.motors}
        
        self.history = []
        self.current_time = 0
        self.state = SimulatorState.PAUSED
        self.paused_motors = {}
        self.failed_motors = {}
        self.pending_decisions = []
        
    def step(self, num_steps: int = 1) -> pd.DataFrame:
        """
        Advance simulation by num_steps and return new data
        """
        if self.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        new_records = []
        
        for _ in range(num_steps):
            step_records = self.factory.step()
            
            # Filter out paused and failed motors from data generation
            active_records = []
            for record in step_records:
                motor_id = record["motor_id"]
                
                # Skip if motor is failed
                if motor_id in self.failed_motors:
                    continue
                
                # Skip if motor is paused (waiting for user decision)
                if motor_id in self.paused_motors:
                    continue
                
                record["time"] = self.current_time
                active_records.append(record)
                
                # Check for critical health in live mode
                if self.config.generation_mode == "live":
                    health = record.get("motor_health", 1.0)
                    if health <= self.alert_threshold and motor_id not in self.pending_decisions:
                        # Pause this motor and add to pending decisions
                        self._pause_motor_for_decision(motor_id, health)
            
            new_records.extend(active_records)
            self.current_time += 1
            
            # Check for automatic maintenance cycles (only in instantaneous mode)
            if self.config.auto_maintenance_enabled and self.config.generation_mode == "instantaneous":
                self._check_and_perform_auto_maintenance()
        
        # Add to history
        self.history.extend(new_records)
        
        # Trim history if too large
        if len(self.history) > self.config.max_history * self.config.num_motors:
            excess = len(self.history) - self.config.max_history * self.config.num_motors
            self.history = self.history[excess:]
        
        return pd.DataFrame(new_records)
    
    def get_history_df(self) -> pd.DataFrame:
        """Get full history as DataFrame"""
        if not self.history:
            return pd.DataFrame()
        
        try:
            return pd.DataFrame(self.history)
        except (ValueError, KeyError) as e:
            # Handle inconsistent data - create empty DataFrame with expected columns
            return pd.DataFrame(columns=[
                'time', 'motor_id', 'motor_health', 'vibration', 'temperature',
                'current', 'voltage', 'rpm', 'load_factor', 'health_state'
            ])
    
    def generate_until_all_critical(self, max_steps: int = 100000) -> pd.DataFrame:
        """
        Instantaneous generation: Generate data until ALL motors complete the specified number of maintenance cycles.
        A maintenance cycle is counted when a motor reaches critical and gets automatic maintenance.
        
        Parameters
        ----------
        max_steps : int
            Maximum steps to prevent infinite loops (default increased for multiple cycles)
            
        Returns
        -------
        pd.DataFrame
            All generated data
        """
        if self.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        new_records = []
        # Track maintenance cycles per motor: {motor_id: cycle_count}
        motor_maintenance_cycles = {motor.motor_id: 0 for motor in self.factory.motors}
        total_motors = self.config.num_motors
        target_cycles = self.config.target_maintenance_cycles
        steps_taken = 0
        
        # Track which motors were critical in previous step to detect entry into critical
        previous_critical_motors = set()
        
        print(f"Starting data generation: {total_motors} motors, {target_cycles} cycle(s) each")
        
        # Continue until all motors complete target number of cycles
        while steps_taken < max_steps:
            # Step simulation
            step_records = self.factory.step()
            
            current_critical_motors = set()
            
            # Add timestamp to each record and check for critical state transitions
            for record in step_records:
                record["time"] = self.current_time
                motor_id = record["motor_id"]
                health_state = record.get("health_state", "Healthy")
                maintenance_event = record.get("maintenance_event")
                
                # Track current critical motors
                if health_state == "Critical":
                    current_critical_motors.add(motor_id)
                
                # Count maintenance events
                if maintenance_event == "automatic_maintenance":
                    motor_maintenance_cycles[motor_id] += 1
                    completed = sum(1 for c in motor_maintenance_cycles.values() if c >= target_cycles)
                    print(f"Motor {motor_id} completed cycle {motor_maintenance_cycles[motor_id]} at step {self.current_time} ({completed}/{total_motors} motors finished)")
            
            new_records.extend(step_records)
            self.current_time += 1
            steps_taken += 1
            
            previous_critical_motors = current_critical_motors
            
            # Check if all motors have completed target cycles
            if all(cycles >= target_cycles for cycles in motor_maintenance_cycles.values()):
                print(f"\n✓ All motors completed {target_cycles} cycle(s)!")
                break
            
            # Progress update every 5000 steps
            if steps_taken % 5000 == 0:
                completed = sum(1 for c in motor_maintenance_cycles.values() if c >= target_cycles)
                print(f"Progress: {steps_taken} steps, {completed}/{total_motors} motors completed")
        
        # Add all records to history
        self.history.extend(new_records)
        
        # Trim history if too large
        if len(self.history) > self.config.max_history * self.config.num_motors:
            excess = len(self.history) - self.config.max_history * self.config.num_motors
            self.history = self.history[excess:]
        
        # Final summary
        cycles_summary = ", ".join([f"M{mid}:{cycles}" for mid, cycles in sorted(motor_maintenance_cycles.items())])
        print(f"\n✓ Generation complete: {steps_taken} steps, {len(new_records)} records")
        print(f"  Maintenance cycles per motor: {cycles_summary}")
        
        return pd.DataFrame(new_records)
    
    def get_recent_history(self, last_n_steps: int = 100) -> pd.DataFrame:
        """Get recent history as DataFrame"""
        if not self.history:
            return pd.DataFrame()
        
        # Get records from last N timesteps
        min_time = max(0, self.current_time - last_n_steps)
        recent = [r for r in self.history if r["time"] >= min_time]
        
        return pd.DataFrame(recent)
    
    def get_motor_status(self) -> pd.DataFrame:
        """Get current status of all motors"""
        if self.factory is None or not self.history:
            return pd.DataFrame()
        
        df = self.get_history_df()
        
        if df.empty:
            return pd.DataFrame()
        
        # Get latest reading for each motor
        latest = df.groupby("motor_id").last().reset_index()
        
        # Add alert status based on health state
        if "health_state" in latest.columns:
            latest["alert"] = latest["health_state"].isin(["Critical", "Warning"])
        else:
            latest["alert"] = False
        
        # Calculate estimated hours to critical (if not already critical)
        if "target_hours_to_critical" in latest.columns:
            latest["est_hours_remaining"] = latest.apply(
                lambda row: max(0, row.get("target_hours_to_critical", 0) - row.get("hours_since_maintenance", 0))
                if row["health_state"] != "Critical" else 0,
                axis=1
            )
        
        return latest
    
    def inject_failure(self, motor_id: int):
        """Inject sudden failure to a specific motor"""
        if self.factory is None:
            raise ValueError("Factory not initialized")
        
        for motor in self.factory.motors:
            if motor.motor_id == motor_id:
                # Drastically reduce motor health
                motor.state.motor_health = 0.1
                motor.state.misalignment += 0.3
                motor.state.friction_coeff *= 2.0
                break
    
    def reset_motor(self, motor_id: int):
        """Reset a motor to healthy state (simulate maintenance)"""
        if self.factory is None:
            raise ValueError("Factory not initialized")
        
        for motor in self.factory.motors:
            if motor.motor_id == motor_id:
                motor.state.motor_health = 1.0
                motor.state.misalignment = 0.05
                motor.state.friction_coeff = REALISTIC_CONFIG["base_friction"]
                # Update last maintenance time
                self.last_maintenance_time[motor_id] = self.current_time
                break
    
    def _check_and_perform_auto_maintenance(self):
        """Check if any motors need automatic maintenance based on cycle period"""
        if self.factory is None:
            return
        
        for motor in self.factory.motors:
            motor_id = motor.motor_id
            last_maintenance = self.last_maintenance_time.get(motor_id, 0)
            time_since_maintenance = self.current_time - last_maintenance
            
            # Perform maintenance if cycle period has elapsed
            if time_since_maintenance >= self.config.maintenance_cycle_period:
                self.reset_motor(motor_id)
    
    def get_alerts(self) -> List[Dict]:
        """Get list of motors with Warning or Critical health status"""
        status = self.get_motor_status()
        
        if status.empty:
            return []
        
        alerts = status[status["alert"]].to_dict("records")
        
        return [
            {
                "motor_id": alert["motor_id"],
                "health_state": alert["health_state"],
                "health": alert["motor_health"],
                "hours_since_maintenance": alert.get("hours_since_maintenance", 0),
                "vibration": alert["vibration"],
                "temperature": alert["temperature"]
            }
            for alert in alerts
        ]
    
    def export_data(self, filepath: str):
        """Export history to CSV"""
        df = self.get_history_df()
        df.to_csv(filepath, index=False)
        return filepath
    
    def pause(self):
        """Pause the simulation"""
        if self.state == SimulatorState.RUNNING:
            self.state = SimulatorState.PAUSED
    
    def resume(self):
        """Resume the simulation"""
        if self.state == SimulatorState.PAUSED and self.factory is not None:
            self.state = SimulatorState.RUNNING
    
    def stop(self):
        """Stop the simulation completely"""
        self.state = SimulatorState.STOPPED
    
    def restart(self):
        """Restart the simulation from beginning"""
        if self.factory is not None:
            self.initialize(self.config)
            self.state = SimulatorState.RUNNING
    
    def _pause_motor_for_decision(self, motor_id: int, health: float):
        """Pause a motor and request user decision on failure vs maintenance"""
        if motor_id not in self.paused_motors:
            self.paused_motors[motor_id] = {
                "health": health,
                "timestamp": self.current_time,
                "reason": "critical_health"
            }
            self.pending_decisions.append(motor_id)
    
    def handle_motor_failure(self, motor_id: int):
        """Mark motor as failed - stops data generation until user re-adds it"""
        if motor_id in self.paused_motors:
            self.failed_motors[motor_id] = {
                "failure_time": self.current_time,
                "health_at_failure": self.paused_motors[motor_id]["health"]
            }
            del self.paused_motors[motor_id]
            if motor_id in self.pending_decisions:
                self.pending_decisions.remove(motor_id)
    
    def handle_motor_maintenance(self, motor_id: int):
        """Perform maintenance on motor and resume data generation"""
        if motor_id in self.paused_motors:
            # Reset motor to healthy state
            self.reset_motor(motor_id)
            del self.paused_motors[motor_id]
            if motor_id in self.pending_decisions:
                self.pending_decisions.remove(motor_id)
    
    def restore_failed_motor(self, motor_id: int):
        """Restore a failed motor back to operation with good health, synced to current time"""
        if motor_id in self.failed_motors:
            # Reset motor to healthy state
            self.reset_motor(motor_id)
            # Remove from failed motors
            del self.failed_motors[motor_id]
            # Motor will now sync with current time on next step
    
    def get_pending_decisions(self) -> List[Dict]:
        """Get list of motors waiting for user decision"""
        decisions = []
        for motor_id in self.pending_decisions:
            if motor_id in self.paused_motors:
                motor_info = self.paused_motors[motor_id]
                decisions.append({
                    "motor_id": motor_id,
                    "health": motor_info["health"],
                    "paused_at_time": motor_info["timestamp"],
                    "hours_paused": (self.current_time - motor_info["timestamp"]) * 5 / 60  # Convert 5-min intervals to hours
                })
        return decisions
    
    def get_failed_motors(self) -> List[Dict]:
        """Get list of failed motors"""
        failed = []
        for motor_id, info in self.failed_motors.items():
            failed.append({
                "motor_id": motor_id,
                "failure_time": info["failure_time"],
                "health_at_failure": info["health_at_failure"],
                "hours_since_failure": (self.current_time - info["failure_time"]) * 5 / 60
            })
        return failed
