from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta


class HealthState(Enum):
    """Motor health categorical states"""
    HEALTHY = "Healthy"
    WARNING = "Warning"
    CRITICAL = "Critical"


class DegradationStage(Enum):
    """Degradation stage in motor lifecycle"""
    STAGE_0_HEALTHY = 0  # 70-85% of life - nearly flat
    STAGE_1_EARLY = 1     # 12-22% of life - power law growth
    STAGE_2_RAPID = 2     # 5-10% of life - exponential decline


@dataclass
class MotorHiddenState:
    """
    Hidden (unobservable) state of the motor system.
    This drives all sensor behavior.
    """
    motor_health: float  # Internal health score: 1.0 (perfect) → 0.0 (failed)
    health_state: HealthState  # Categorical state for reporting
    degradation_stage: DegradationStage  # Current degradation stage
    load_factor: float     # operational load multiplier
    misalignment: float    # mechanical misalignment
    friction_coeff: float  # internal friction
    hours_since_maintenance: float  # Operating hours since last maintenance
    target_hours_to_critical: float  # Total target lifespan for this motor
    
    # Stage transition hours (calculated during initialization)
    stage_0_duration_hours: float  # Duration of healthy stage
    stage_1_duration_hours: float  # Duration of early degradation
    stage_2_duration_hours: float  # Duration of rapid decline
    
    # Stage-specific parameters
    stage_1_power_exponent: float  # Power law exponent b for stage 1
    stage_2_exp_coefficient: float  # Exponential coefficient c for stage 2
