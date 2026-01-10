"""
Sensor Imperfection Models - Stateful sensor failures

Real sensors fail independently of machine health.
This module simulates:
- Bias drift (slow shift in readings)
- Noise degradation (sensor becomes noisy over time)
- Flatlines (sensor stuck at value)
- Intermittent failures
"""
import numpy as np
from typing import Optional, Dict


class SensorImperfectionState:
    """
    Tracks the state of sensor imperfections for a single sensor.
    """
    def __init__(self, sensor_name: str):
        self.sensor_name = sensor_name
        
        # Bias drift (accumulates over time)
        self.accumulated_bias = 0.0
        self.bias_drift_rate = 0.0  # Set when drift starts
        
        # Noise degradation
        self.noise_multiplier = 1.0
        
        # Flatline state
        self.is_flatlined = False
        self.flatline_value = None
        self.flatline_countdown = 0
        
        # Intermittent failure
        self.is_intermittent = False
        self.intermittent_countdown = 0


class SensorImperfectionSimulator:
    """
    Manages stateful sensor imperfections for all sensors in a motor.
    """
    
    def __init__(self, enable_imperfections: bool = True):
        self.enable_imperfections = enable_imperfections
        self.sensors: Dict[str, SensorImperfectionState] = {}
        self.timestep = 0
        
        # Failure probabilities (per 1000 steps)
        self.drift_start_prob = 0.002      # 0.2% per step
        self.flatline_start_prob = 0.0005  # 0.05% per step
        self.intermittent_prob = 0.001     # 0.1% per step
        
    def register_sensor(self, sensor_name: str):
        """Register a sensor for imperfection tracking"""
        if sensor_name not in self.sensors:
            self.sensors[sensor_name] = SensorImperfectionState(sensor_name)
    
    def update(self):
        """Update sensor states (call once per timestep)"""
        if not self.enable_imperfections:
            return
        
        self.timestep += 1
        
        for sensor_name, state in self.sensors.items():
            self._update_sensor_state(state)
    
    def _update_sensor_state(self, state: SensorImperfectionState):
        """Update a single sensor's imperfection state"""
        
        # Bias drift
        if state.bias_drift_rate == 0 and np.random.random() < self.drift_start_prob:
            # Start drifting
            state.bias_drift_rate = np.random.uniform(1e-4, 5e-4)
        
        if state.bias_drift_rate > 0:
            state.accumulated_bias += state.bias_drift_rate * np.random.choice([-1, 1])
        
        # Flatline
        if not state.is_flatlined and np.random.random() < self.flatline_start_prob:
            state.is_flatlined = True
            state.flatline_countdown = np.random.randint(10, 50)  # Lasts 10-50 steps
        
        if state.is_flatlined:
            state.flatline_countdown -= 1
            if state.flatline_countdown <= 0:
                state.is_flatlined = False
                state.flatline_value = None
        
        # Intermittent failure
        if not state.is_intermittent and np.random.random() < self.intermittent_prob:
            state.is_intermittent = True
            state.intermittent_countdown = np.random.randint(5, 20)
        
        if state.is_intermittent:
            state.intermittent_countdown -= 1
            if state.intermittent_countdown <= 0:
                state.is_intermittent = False
    
    def apply_imperfections(self, sensor_name: str, value: float) -> Optional[float]:
        """
        Apply sensor imperfections to a reading.
        
        Args:
            sensor_name: Name of the sensor
            value: Clean sensor reading
        
        Returns:
            Modified value, or None if sensor failed
        """
        if not self.enable_imperfections or value is None:
            return value
        
        if sensor_name not in self.sensors:
            self.register_sensor(sensor_name)
        
        state = self.sensors[sensor_name]
        
        # Intermittent failure (reading drops completely)
        if state.is_intermittent and np.random.random() < 0.3:  # 30% drop rate when intermittent
            return None
        
        # Flatline (sensor stuck)
        if state.is_flatlined:
            if state.flatline_value is None:
                state.flatline_value = value  # Capture first value
            return state.flatline_value
        
        # Apply bias drift
        value += state.accumulated_bias
        
        # Apply noise degradation (if sensor is degrading, noise increases)
        if state.noise_multiplier > 1.0:
            # Already noisy, don't modify further here
            pass
        
        return value
    
    def get_sensor_status(self) -> Dict[str, Dict]:
        """Get current status of all sensors for debugging/visualization"""
        status = {}
        for sensor_name, state in self.sensors.items():
            status[sensor_name] = {
                "bias": state.accumulated_bias,
                "flatlined": state.is_flatlined,
                "intermittent": state.is_intermittent,
                "drift_rate": state.bias_drift_rate
            }
        return status
