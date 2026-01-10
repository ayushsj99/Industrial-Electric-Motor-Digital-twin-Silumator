import numpy as np
from simulator.state import HealthState, DegradationStage


def determine_health_state(health_value, healthy_threshold=0.7, warning_threshold=0.4):
    """
    Convert continuous health value to categorical state.
    
    Args:
        health_value: Continuous health [0, 1]
        healthy_threshold: Threshold above which motor is healthy
        warning_threshold: Threshold below which motor is critical
    
    Returns:
        HealthState enum value
    """
    if health_value >= healthy_threshold:
        return HealthState.HEALTHY
    elif health_value >= warning_threshold:
        return HealthState.WARNING
    else:
        return HealthState.CRITICAL


def determine_degradation_stage(hours_since_maintenance, stage_0_duration, stage_1_duration, stage_2_duration):
    """
    Determine which degradation stage the motor is in based on operating hours.
    
    Args:
        hours_since_maintenance: Current operating hours
        stage_0_duration: Duration of stage 0 (healthy)
        stage_1_duration: Duration of stage 1 (early degradation)
        stage_2_duration: Duration of stage 2 (rapid decline)
    
    Returns:
        DegradationStage enum value
    """
    if hours_since_maintenance < stage_0_duration:
        return DegradationStage.STAGE_0_HEALTHY
    elif hours_since_maintenance < stage_0_duration + stage_1_duration:
        return DegradationStage.STAGE_1_EARLY
    else:
        return DegradationStage.STAGE_2_RAPID


def update_motor_health(
    current_health,
    hours_since_maintenance,
    degradation_stage,
    stage_0_duration,
    stage_1_duration,
    stage_2_duration,
    stage_1_power_exp,
    stage_2_exp_coeff,
    config
):
    """
    Three-stage degradation model with realistic stochasticity.
    
    Stage 0 (70-85% of life): Nearly flat with noise - H ≈ 0.95 + noise
    Stage 1 (12-22% of life): Power law growth - H = 0.95 - a·t^b, b∈[1.5, 3.5]
    Stage 2 (5-10% of life): Exponential decline - H = base - 0.5·exp(c·t)
    
    Args:
        current_health: Current health value
        hours_since_maintenance: Operating hours since maintenance
        degradation_stage: Current DegradationStage
        stage_0_duration: Duration of stage 0 in hours
        stage_1_duration: Duration of stage 1 in hours
        stage_2_duration: Duration of stage 2 in hours
        stage_1_power_exp: Power exponent for stage 1
        stage_2_exp_coeff: Exponential coefficient for stage 2
        config: Configuration dictionary
    
    Returns:
        New health value
    """
    time_step_hours = config.get("time_step_minutes", 5) / 60.0
    
    if degradation_stage == DegradationStage.STAGE_0_HEALTHY:
        # Stage 0: Nearly flat with small noise
        base_health = config.get("stage_0_base_health", 0.95)
        noise_std = config.get("stage_0_noise_std", 0.01)
        
        # Very small deterministic decay (to ensure eventual transition)
        tiny_decay = 0.05 / stage_0_duration * time_step_hours if stage_0_duration > 0 else 0
        
        # Add stochastic noise (can go up or down slightly)
        noise = np.random.normal(0, noise_std * time_step_hours)
        
        new_health = current_health - tiny_decay + noise
        # Keep health bounded near perfect
        new_health = np.clip(new_health, base_health - 0.03, base_health + 0.02)
        
    elif degradation_stage == DegradationStage.STAGE_1_EARLY:
        # Stage 1: Power law degradation - H = initial_health - a·t^b
        # where t is time within this stage
        time_in_stage = hours_since_maintenance - stage_0_duration
        
        # Calculate coefficient 'a' such that health degrades from ~0.95 to ~0.5
        # over the stage duration
        health_drop_needed = 0.45  # Drop from 0.95 to 0.50
        
        if stage_1_duration > 0:
            # a = health_drop / (duration^b)
            a = health_drop_needed / (stage_1_duration ** stage_1_power_exp)
        else:
            a = 0
        
        # Calculate expected health at current time
        health_from_model = 0.95 - a * (time_in_stage ** stage_1_power_exp)
        
        # Add stochastic variation (±2%)
        noise = np.random.normal(0, 0.02)
        new_health = health_from_model + noise
        
        # Ensure monotonic decrease (health can't increase in this stage)
        new_health = min(new_health, current_health)
        
    else:  # Stage 2: Rapid decline
        # Stage 2: Exponential decline - H = base - 0.5·exp(c·t)
        time_in_stage = hours_since_maintenance - stage_0_duration - stage_1_duration
        
        # Start from ~0.5 and drop to ~0.3-0.4 (critical threshold)
        initial_stage2_health = 0.50
        target_final_health = 0.35
        
        # Calculate exponential coefficient
        # 0.50 - 0.5·exp(c·duration) = 0.35
        # 0.5·exp(c·duration) = 0.15
        # exp(c·duration) = 0.30
        # c = ln(0.30) / duration
        if stage_2_duration > 0:
            c = np.log(0.30) / stage_2_duration
        else:
            c = -0.1
        
        # Exponential decay
        decay = 0.5 * np.exp(c * time_in_stage)
        health_from_model = initial_stage2_health - decay
        
        # Add noise (smaller as we approach failure)
        noise = np.random.normal(0, 0.01)
        new_health = health_from_model + noise
        
        # Ensure monotonic decrease and don't go below 0
        new_health = min(new_health, current_health)
        new_health = max(0.0, new_health)
    
    return new_health


def update_friction(base_friction, motor_health, k_friction):
    """
    Friction increases as motor health deteriorates.
    """
    return base_friction + k_friction * (1 - motor_health)


def update_temperature(temp, ambient_temp, friction, load, alpha, beta):
    """
    Temperature rises due to friction & load, cools towards ambient.
    """
    heat_generated = alpha * friction * load
    cooling = beta * (temp - ambient_temp)
    return temp + heat_generated - cooling


def compute_vibration(motor_health, misalignment, v_base, k_health, k_align, duration=20, sample_rate=10):
    """
    Compute aggregated vibration reading over a duration.
    Simulates taking multiple samples over 20 seconds and computing RMS.
    
    Args:
        motor_health: Current motor health [0, 1]
        misalignment: Misalignment factor
        v_base: Baseline vibration
        k_health: Health sensitivity factor
        k_align: Alignment sensitivity factor
        duration: Sampling duration in seconds (default 20)
        sample_rate: Samples per second (default 10)
    
    Returns:
        RMS vibration value over the sampling period
    """
    # Base vibration level
    base_vib = v_base + k_health * (1 - motor_health) ** 2 + k_align * misalignment
    
    # Generate multiple samples to simulate 20-second reading
    num_samples = duration * sample_rate  # 20 seconds * 10 Hz = 200 samples
    
    # Each sample has small random variation
    samples = []
    for _ in range(num_samples):
        # Add temporal variation (simulating rotation cycles, etc.)
        temporal_noise = np.random.normal(0, base_vib * 0.05)
        sample = base_vib + temporal_noise
        samples.append(sample)
    
    # Compute RMS (Root Mean Square) of samples
    rms_vibration = np.sqrt(np.mean(np.array(samples) ** 2))
    
    return rms_vibration


def compute_current(base_current, load, motor_health, k_current):
    """
    Mechanical resistance increases electrical current draw.
    """
    return base_current * load * (1 + k_current * (1 - motor_health))


def compute_rpm(nominal_rpm, misalignment):
    """
    Misalignment slightly reduces effective RPM.
    """
    return nominal_rpm * (1 - 0.05 * misalignment)
