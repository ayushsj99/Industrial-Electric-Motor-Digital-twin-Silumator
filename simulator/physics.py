import numpy as np


def update_bearing_health(
    health, 
    base_decay, 
    load, 
    misalignment,
    micro_damage_std=0.0001,
    shock_prob=0.008,
    shock_scale=0.01
):
    """
    Stochastic bearing health degradation with burst damage.
    
    Real bearings degrade through:
    - Slow wear (base_decay)
    - Micro-damage accumulation (random)
    - Occasional shock events (pitting, cracks)
    - Acceleration near failure
    
    Args:
        health: Current bearing health [0, 1]
        base_decay: Base decay rate
        load: Load factor
        misalignment: Misalignment factor
        micro_damage_std: Standard deviation of micro-damage
        shock_prob: Probability of shock event per timestep
        shock_scale: Base magnitude of shock damage
    
    Returns:
        Updated health value
    """
    # Base deterministic decay (load and misalignment dependent)
    base_degradation = base_decay * load * (1 + misalignment)
    
    # Micro-damage: small random hits every step
    # Mean = 0, so it oscillates but has net effect over time
    micro_damage = np.abs(np.random.normal(0, micro_damage_std))
    
    # Shock damage: rare but larger drops
    # Probability and magnitude increase as health decreases (damage begets damage)
    shock_damage = 0.0
    if np.random.random() < shock_prob:
        # Shock magnitude scales with degradation level
        degradation_factor = (1 - health) ** 0.5  # Worse health = bigger shocks
        shock_damage = shock_scale * (1 + degradation_factor)
    
    # Total degradation
    total_degradation = base_degradation + micro_damage + shock_damage
    
    # Accelerated degradation near failure (positive feedback)
    # As health drops below 0.3, degradation accelerates
    if health < 0.3:
        acceleration_factor = 1.0 + (0.3 - health) * 2.0  # Up to 1.6x faster
        total_degradation *= acceleration_factor
    
    return max(0.0, health - total_degradation)


def update_friction(base_friction, bearing_health, k_friction):
    """
    Friction increases as bearing health deteriorates.
    """
    return base_friction + k_friction * (1 - bearing_health)


def update_temperature(temp, ambient_temp, friction, load, alpha, beta):
    """
    Temperature rises due to friction & load, cools towards ambient.
    """
    heat_generated = alpha * friction * load
    cooling = beta * (temp - ambient_temp)
    return temp + heat_generated - cooling


def compute_vibration(bearing_health, misalignment, v_base, k_health, k_align):
    """
    Vibration grows non-linearly as bearing health declines.
    """
    return v_base + k_health * (1 - bearing_health) ** 2 + k_align * misalignment


def compute_current(base_current, load, bearing_health, k_current):
    """
    Mechanical resistance increases electrical current draw.
    """
    return base_current * load * (1 + k_current * (1 - bearing_health))


def compute_rpm(nominal_rpm, misalignment):
    """
    Misalignment slightly reduces effective RPM.
    """
    return nominal_rpm * (1 - 0.05 * misalignment)
