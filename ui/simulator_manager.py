"""
Simulator Manager - Simplified coordinator using strategy pattern
"""
import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
import sys
import os

# Add project root and strategies to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
strategies_path = os.path.join(os.path.dirname(__file__), 'strategies')
for path in [project_root, strategies_path]:
    if path not in sys.path:
        sys.path.append(path)

from simulator.factory import FactorySimulator
from strategies.live_mode_strategy import LiveModeStrategy
from strategies.instantaneous_strategy import InstantaneousStrategy


@dataclass
class SimulatorConfig:
    """Configuration for the simulator"""
    num_motors: int = 5
    degradation_speed: float = 1.0
    noise_level: float = 1.0
    load_factor: float = 1.0
    max_history: int = 100000  # Increased for instantaneous mode large datasets
    auto_maintenance_enabled: bool = True
    maintenance_cycle_period: int = 3600
    generation_mode: str = "live"  # "live" or "instantaneous"
    target_maintenance_cycles: int = 1
    warning_threshold: float = 0.4
    critical_threshold: float = 0.2


class SimulatorState:
    """Simulation states"""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


class SimulatorManager:
    """Manages the lifecycle of the factory simulator using strategy pattern"""
    
    def __init__(self):
        self.factory: Optional[FactorySimulator] = None
        self.history: List[Dict] = []
        self.current_time: int = 0
        self.config: SimulatorConfig = SimulatorConfig()
        self.state: str = SimulatorState.STOPPED
        self.alert_threshold: float = 0.3
        self.last_maintenance_time: Dict[int, int] = {}
        
        # Live mode specific state
        self.paused_motors: Dict[int, Dict] = {}
        self.failed_motors: Dict[int, Dict] = {}
        self.pending_decisions: List[int] = []
        
        # Strategy pattern
        self.strategy = None
        
    def initialize(self, config: SimulatorConfig):
        """Initialize factory simulator with strategy"""
        self.config = config
        
        # Create strategy based on generation mode
        if config.generation_mode == "instantaneous":
            self.strategy = InstantaneousStrategy(self)
        else:
            self.strategy = LiveModeStrategy(self)
        
        # Initialize factory using strategy
        self.factory = self.strategy.initialize_factory(config)
        
        # Initialize tracking
        self.last_maintenance_time = {motor.motor_id: 0 for motor in self.factory.motors}
        self.history = []
        self.current_time = 0
        self.state = SimulatorState.PAUSED
        self.paused_motors = {}
        self.failed_motors = {}
        self.pending_decisions = []
    
    def update_configuration(self, config: SimulatorConfig):
        """Update configuration, reinitialize if mode changed"""
        if (self.factory is None or self.strategy is None or 
            config.generation_mode != self.config.generation_mode):
            self.initialize(config)
            return
        
        # Simple parameter updates
        self.config = config
        if self.factory and self.factory.motors:
            for motor in self.factory.motors:
                motor.state.load_factor = config.load_factor
    
    def step(self, num_steps: int = 1) -> pd.DataFrame:
        """Advance simulation using current strategy"""
        if self.strategy is None:
            raise ValueError("Simulator not initialized. Call initialize() first.")
        return self.strategy.step(num_steps)
    
    def generate_until_all_critical(self, max_steps: int = 100000) -> pd.DataFrame:
        """Generate data until all motors complete target cycles - instantaneous mode only"""
        if not isinstance(self.strategy, InstantaneousStrategy):
            raise ValueError("generate_until_all_critical only available in instantaneous mode")
        return self.strategy.generate_until_all_critical(max_steps)
    
    def reset_motor(self, motor_id: int):
        """Reset motor using current strategy"""
        if self.strategy is None:
            raise ValueError("Simulator not initialized. Call initialize() first.")
        self.strategy.reset_motor(motor_id)
    
    def get_history_df(self) -> pd.DataFrame:
        """Get full history as DataFrame"""
        if not self.history:
            return pd.DataFrame()
        try:
            return pd.DataFrame(self.history)
        except (ValueError, KeyError):
            return pd.DataFrame(columns=[
                'time', 'motor_id', 'motor_health', 'vibration', 'temperature',
                'current', 'voltage', 'rpm', 'load_factor', 'health_state'
            ])
    
    def get_recent_history(self, last_n_steps: int = 100) -> pd.DataFrame:
        """Get recent history as DataFrame"""
        if not self.history:
            return pd.DataFrame()
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
        
        # Add alert status
        if "health_state" in latest.columns:
            latest["alert"] = latest["health_state"].isin(["Critical", "Warning"])
        else:
            latest["alert"] = False
        
        return latest
    
    def get_alerts(self) -> List[Dict]:
        """Get current alerts for motors with health issues"""
        alerts = []
        
        if self.factory is None or not self.history:
            return alerts
        
        # Get current motor status
        status_df = self.get_motor_status()
        
        if status_df.empty:
            return alerts
        
        # Generate alerts for motors below threshold
        for _, motor in status_df.iterrows():
            motor_id = motor.get('motor_id')
            
            # Check health-based alerts
            if 'motor_health' in motor and motor['motor_health'] < self.alert_threshold:
                health_level = motor['motor_health']
                if health_level <= 0.1:
                    severity = "Critical"
                    message = f"Motor {motor_id} health critically low ({health_level:.1%})"
                elif health_level <= 0.3:
                    severity = "Warning"
                    message = f"Motor {motor_id} health degraded ({health_level:.1%})"
                else:
                    severity = "Info"
                    message = f"Motor {motor_id} health below threshold ({health_level:.1%})"
                
                alerts.append({
                    'motor_id': motor_id,
                    'severity': severity,
                    'message': message,
                    'timestamp': self.current_time,
                    'value': health_level
                })
            
            # Check for high temperature alerts
            if 'temperature' in motor and motor['temperature'] > 90:
                alerts.append({
                    'motor_id': motor_id,
                    'severity': "Warning",
                    'message': f"Motor {motor_id} temperature high ({motor['temperature']:.1f}°C)",
                    'timestamp': self.current_time,
                    'value': motor['temperature']
                })
            
            # Check for high vibration alerts
            if 'vibration' in motor and motor['vibration'] > 2.0:
                alerts.append({
                    'motor_id': motor_id,
                    'severity': "Warning", 
                    'message': f"Motor {motor_id} vibration excessive ({motor['vibration']:.2f})",
                    'timestamp': self.current_time,
                    'value': motor['vibration']
                })
        
        # Add pending decision alerts (for live mode)
        for decision in self.get_pending_decisions():
            alerts.append({
                'motor_id': decision['motor_id'],
                'severity': "Action Required",
                'message': f"Motor {decision['motor_id']} requires maintenance decision",
                'timestamp': decision['paused_at_time'],
                'value': decision['health']
            })
        
        return alerts
    
    def inject_failure(self, motor_id: int):
        """Inject sudden failure to a specific motor"""
        if self.factory is None:
            raise ValueError("Factory not initialized")
        
        for motor in self.factory.motors:
            if motor.motor_id == motor_id:
                motor.state.motor_health = 0.1
                motor.state.misalignment += 0.3
                motor.state.friction_coeff *= 2.0
                break
    
    def export_data(self) -> str:
        """Export history as CSV string"""
        df = self.get_history_df()
        return df.to_csv(index=False)
    
    def get_export_filename(self) -> str:
        """Generate filename for export with timestamp"""
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        return f"industrial_simulator_export_{timestamp}.csv"
    
    # State management
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
    
    # Live mode helper methods (only used by LiveModeStrategy)
    def _pause_motor_for_decision(self, motor_id: int, health: float):
        """Pause a motor and request user decision"""
        if motor_id not in self.paused_motors:
            self.paused_motors[motor_id] = {
                "health": health,
                "timestamp": self.current_time,
                "reason": "critical_health"
            }
            self.pending_decisions.append(motor_id)
    
    def handle_motor_failure(self, motor_id: int):
        """Mark motor as failed"""
        if motor_id in self.paused_motors:
            self.failed_motors[motor_id] = {
                "failure_time": self.current_time,
                "health_at_failure": self.paused_motors[motor_id]["health"]
            }
            del self.paused_motors[motor_id]
            if motor_id in self.pending_decisions:
                self.pending_decisions.remove(motor_id)
    
    def handle_motor_maintenance(self, motor_id: int):
        """Perform maintenance on motor and resume"""
        if motor_id in self.paused_motors:
            self.reset_motor(motor_id)
            del self.paused_motors[motor_id]
            if motor_id in self.pending_decisions:
                self.pending_decisions.remove(motor_id)
    
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
                    "hours_paused": (self.current_time - motor_info["timestamp"]) * 5 / 60
                })
        return decisions