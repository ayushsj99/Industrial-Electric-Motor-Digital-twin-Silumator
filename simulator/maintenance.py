"""
Maintenance Event System

Simulates realistic maintenance interventions:
- Partial health recovery (not perfect reset)
- Immediate vibration drop
- Resumed degradation (often faster than before)
- Post-maintenance behavior changes
"""
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class MaintenanceEvent:
    """Record of a maintenance event"""
    timestep: int
    motor_id: int
    pre_health: float
    post_health: float
    maintenance_type: str  # 'bearing_replacement', 'lubrication', 'alignment'


class MaintenanceScheduler:
    """
    Manages scheduled and reactive maintenance events
    """
    
    def __init__(self, enable_maintenance: bool = True):
        self.enable_maintenance = enable_maintenance
        self.events: List[MaintenanceEvent] = []
        
        # Thresholds for reactive maintenance
        self.critical_health_threshold = 0.25
        self.reactive_prob_per_step = 0.15  # 15% chance to intervene if critical
        
        # Scheduled maintenance parameters
        self.scheduled_interval = 500  # Every 500 timesteps
        self.scheduled_variance = 100   # ±100 timesteps
        
    def should_perform_maintenance(
        self, 
        timestep: int, 
        motor_id: int, 
        bearing_health: float
    ) -> Optional[str]:
        """
        Decide if maintenance should be performed on a motor.
        
        Returns:
            Maintenance type if maintenance should occur, None otherwise
        """
        if not self.enable_maintenance:
            return None
        
        # Reactive maintenance (critical health)
        if bearing_health < self.critical_health_threshold:
            if np.random.random() < self.reactive_prob_per_step:
                return "bearing_replacement"
        
        # Scheduled maintenance (periodic)
        if timestep % self.scheduled_interval < 10:  # Small window
            if np.random.random() < 0.1:  # 10% chance in window
                return "lubrication"
        
        return None
    
    def perform_maintenance(
        self,
        motor,
        maintenance_type: str,
        timestep: int
    ) -> MaintenanceEvent:
        """
        Execute maintenance on a motor.
        
        Args:
            motor: Motor object to maintain
            maintenance_type: Type of maintenance
            timestep: Current simulation timestep
        
        Returns:
            MaintenanceEvent record
        """
        pre_health = motor.state.bearing_health
        
        if maintenance_type == "bearing_replacement":
            # Major intervention
            # Health improves significantly but not to perfect
            motor.state.bearing_health = np.random.uniform(0.75, 0.90)
            
            # Reset misalignment partially
            motor.state.misalignment *= 0.3
            
            # Reset friction
            motor.state.friction_coeff = motor.config["base_friction"] * 1.1
            
        elif maintenance_type == "lubrication":
            # Minor intervention
            # Small health boost
            motor.state.bearing_health = min(1.0, motor.state.bearing_health + 0.1)
            
            # Reduce friction temporarily
            motor.state.friction_coeff *= 0.8
            
        elif maintenance_type == "alignment":
            # Alignment correction
            motor.state.misalignment *= 0.5
            motor.state.bearing_health = min(1.0, motor.state.bearing_health + 0.05)
        
        post_health = motor.state.bearing_health
        
        # Record event
        event = MaintenanceEvent(
            timestep=timestep,
            motor_id=motor.motor_id,
            pre_health=pre_health,
            post_health=post_health,
            maintenance_type=maintenance_type
        )
        self.events.append(event)
        
        return event
    
    def get_maintenance_history(self) -> List[MaintenanceEvent]:
        """Get all maintenance events"""
        return self.events
    
    def get_motor_maintenance_count(self, motor_id: int) -> int:
        """Count maintenance events for a specific motor"""
        return sum(1 for event in self.events if event.motor_id == motor_id)
