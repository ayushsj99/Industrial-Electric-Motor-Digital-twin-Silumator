REALISTIC_CONFIG = {
    # Environment
    "ambient_temp": 25.0,

    # ------------------------
    # Degradation (CALIBRATED)
    # ------------------------
    # Mean lifetime ≈ 206 cycles (FD001)
    "base_decay": 0.0045,
    "base_friction": 0.05,
    "k_friction": 0.4,

    # Temperature dynamics
    "alpha": 0.6,
    "beta": 0.15,

    # Vibration (nonlinear growth)
    "v_base": 0.5,
    "k_v_health": 5.0,
    "k_v_align": 2.5,

    # Electrical load
    "base_current": 10.0,
    "k_current": 1.0,

    # RPM
    "nominal_rpm": 1800,

    # ------------------------
    # Sensor Noise (FD001-like)
    # ------------------------
    "noise_temperature": 0.15,
    "noise_vibration": 0.04,
    "noise_current": 0.12,
    "noise_rpm": 3.0,

    # Rare spikes (still realistic)
    "spike_prob": 0.002,
    "vibration_spike": 1.2,

    # Missing data (rare but present)
    "drop_prob": 0.003,

    # Slow sensor drift
    "temp_drift": 1e-4,
    "vibration_drift": 5e-5,
}
