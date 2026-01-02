DEFAULT_CONFIG = {
    # Environment
    "ambient_temp": 25.0,

    # Degradation & physics
    "base_decay": 0.0001,
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
    # Phase 2: Sensor Noise
    # ------------------------
    # Sensor noise (temporarily increased)
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
