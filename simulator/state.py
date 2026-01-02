from dataclasses import dataclass

@dataclass
class MotorHiddenState:
    """
    Hidden (unobservable) state of the motor-bearings system.
    This drives all sensor behavior.
    """
    bearing_health: float  # 1.0 (perfect) → 0.0 (failed)
    load_factor: float     # operational load multiplier
    misalignment: float    # mechanical misalignment
    friction_coeff: float  # internal friction
