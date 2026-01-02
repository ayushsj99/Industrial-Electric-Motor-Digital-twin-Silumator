def update_bearing_health(health, base_decay, load, misalignment):
    """
    Bearing health degrades faster under load and misalignment.
    """
    degradation = base_decay * load * (1 + misalignment)
    return max(0.0, health - degradation)


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
