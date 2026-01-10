DEFAULT_CONFIG = {
    # Environment
    "ambient_temp": 25.0,

    # ------------------------
    # Time Configuration
    # ------------------------
    "time_step_minutes": 5,  # Each step represents 5 minutes
    "vibration_sample_duration": 20,  # Sample vibration for 20 seconds
    "vibration_sample_rate": 10,  # 10 samples per second for vibration
    
    # ------------------------
    # Health State Thresholds
    # ------------------------
    "healthy_threshold": 0.7,  # Above 0.7 = Healthy
    "warning_threshold": 0.4,  # 0.4-0.7 = Warning, below 0.4 = Critical
    
    # ------------------------
    # Lifespan Distribution (Lognormal)
    # ------------------------
    "mean_lifespan_years": 3.0,  # Mean: 2-4 years
    "std_lifespan_years": 1.15,  # Std: 0.8-1.5 years (~38% CV)
    "min_lifespan_years": 1.5,   # Minimum allowed lifespan
    "max_lifespan_years": 6.0,   # Maximum allowed lifespan
    
    # ------------------------
    # Three-Stage Degradation Model
    # ------------------------
    # Stage 0: Healthy (70-85% of life) - Nearly flat
    "stage_0_min_pct": 0.70,  # Minimum 70% of life
    "stage_0_max_pct": 0.85,  # Maximum 85% of life
    "stage_0_base_health": 0.95,  # Start near perfect health
    "stage_0_noise_std": 0.01,  # Small random noise
    
    # Stage 1: Early Degradation (12-22% of life) - Power law
    "stage_1_min_pct": 0.12,
    "stage_1_max_pct": 0.22,
    "stage_1_power_exp_min": 1.5,  # Power exponent b range
    "stage_1_power_exp_max": 3.5,
    
    # Stage 2: Rapid Decline (5-10% of life) - Exponential
    "stage_2_min_pct": 0.05,
    "stage_2_max_pct": 0.10,
    
    # ------------------------
    # Degradation & physics
    # ------------------------
    "base_friction": 0.05,
    "k_friction": 0.4,
    "alpha": 0.8,
    "beta": 0.1,

    # Vibration
    "v_base": 0.5,
    "k_v_health": 6.0,
    "k_v_align": 3.0,

    # Electrical
    "base_current": 10.0,
    "k_current": 1.2,

    # RPM
    "nominal_rpm": 1800,

    # ------------------------
    # Sensor Noise
    # ------------------------
    "noise_temperature": 0.6,
    "noise_vibration": 0.15,
    "noise_current": 0.4,
    "noise_rpm": 8.0,

    # Spikes
    "spike_prob": 0.005,
    "vibration_spike": 3.0,

    # Missing data
    "drop_prob": 0.01,

    # Drift
    "temp_drift": 5e-4,
    "vibration_drift": 2e-4

}
