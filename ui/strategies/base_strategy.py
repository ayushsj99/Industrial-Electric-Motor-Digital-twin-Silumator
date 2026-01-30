"""
Base strategy interface for simulation modes
"""
from abc import ABC, abstractmethod
from typing import Optional
import pandas as pd


class SimulationStrategy(ABC):
    """Base class for simulation strategies"""
    
    def __init__(self, manager):
        self.manager = manager
    
    @abstractmethod
    def step(self, num_steps: int = 1) -> pd.DataFrame:
        """Advance simulation by num_steps"""
        pass
    
    @abstractmethod
    def handle_critical_motor(self, motor_id: int, health: float) -> bool:
        """
        Handle a motor reaching critical state
        Returns True if motor should continue, False if paused/stopped
        """
        pass
    
    @abstractmethod
    def should_perform_maintenance(self, motor_id: int) -> bool:
        """Check if maintenance should be performed on a motor"""
        pass
    
    @abstractmethod
    def reset_motor(self, motor_id: int):
        """Reset a motor to healthy state"""
        pass
    
    @abstractmethod
    def initialize_factory(self, config):
        """Initialize factory with mode-specific settings"""
        pass