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
        
    def step(self, num_steps: int = 1) -> pd.DataFrame:
        """
        Advance simulation by num_steps and return new data
        """
        if self.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        new_records = []
        
        for _ in range(num_steps):
            step_records = self.factory.step()
            
            # Add timestamp to each record
            for record in step_records:
                record["time"] = self.current_time
            
            new_records.extend(step_records)
            self.current_time += 1
            
            # Check for automatic maintenance cycles
            if self.config.auto_maintenance_enabled:
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
        return pd.DataFrame(self.history)
    
    def generate_until_all_critical(self, max_steps: int = 50000) -> pd.DataFrame:
        """
        Instantaneous generation: Generate data until ALL motors reach critical stage.
        Motors that reach critical first will auto-reset and continue until the last motor reaches critical.
        
        Parameters
        ----------
        max_steps : int
            Maximum steps to prevent infinite loops
            
        Returns
        -------
        pd.DataFrame
            All generated data
        """
        if self.factory is None:
            raise ValueError("Factory not initialized. Call initialize() first.")
        
        new_records = []
        motors_reached_critical = set()
        total_motors = self.config.num_motors
        steps_taken = 0
        
        while len(motors_reached_critical) < total_motors and steps_taken < max_steps:
            # Step simulation
            step_records = self.factory.step()
            
            # Add timestamp to each record
            for record in step_records:
                record["time"] = self.current_time
                
                # Check if this motor reached critical for the first time
                motor_id = record["motor_id"]
                health_state = record.get("health_state", "Healthy")
                
                if health_state == "Critical" and motor_id not in motors_reached_critical:
                    motors_reached_critical.add(motor_id)
                    print(f"Motor {motor_id} reached critical at step {self.current_time} ({len(motors_reached_critical)}/{total_motors})")
            
            new_records.extend(step_records)
            self.current_time += 1
            steps_taken += 1
            
            # Check for automatic maintenance (motors will auto-reset)
            if self.config.auto_maintenance_enabled:
                self._check_and_perform_auto_maintenance()
        
        # Add all records to history
        self.history.extend(new_records)
        
        # Trim history if too large
        if len(self.history) > self.config.max_history * self.config.num_motors:
            excess = len(self.history) - self.config.max_history * self.config.num_motors
            self.history = self.history[excess:]
        
        print(f"\n✓ Generation complete: {steps_taken} steps, all {total_motors} motors reached critical")
        
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
        
        # Get latest reading for each motor
        latest = df.groupby("motor_id").last().reset_index()
        
        # Add alert status based on health state
        latest["alert"] = latest["health_state"].isin(["Critical", "Warning"])
        
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
