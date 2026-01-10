"""
Priors learned from real-world data (NASA C-MAPSS FD001).

These priors describe:
- how machines start (initial conditions)
- how degradation behaves structurally
- what assumptions are data-backed

They do NOT execute logic.
They are consumed by the simulator during initialization.
"""

# -------------------------------
# Phase 4B — Initial Condition Priors
# -------------------------------

DEFAULT_HIDDEN_STATE_PRIORS = {
    # Engines start healthy, but not identical
    "motor_health": {
        "distribution": "uniform",
        "min": 0.92,
        "max": 1.00
    },

    # Load varies slightly across machines
    "load_factor": {
        "distribution": "normal",
        "mean": 1.0,
        "std": 0.1,
        "clip": (0.8, 1.3)
    },

    # Small mechanical imperfections are normal
    "misalignment": {
        "distribution": "normal",
        "mean": 0.05,
        "std": 0.03,
        "clip": (0.0, 0.2)
    }
}


# -------------------------------
# Phase 4A — Degradation Priors
# -------------------------------

DEFAULT_DEGRADATION_PRIORS = {
    # Mean lifetime ≈ 206 cycles (FD001)
    "mean_lifetime_cycles": 206,

    # Natural fleet variability (≈ ±22%)
    "lifetime_std_cycles": 46,

    # Base decay implied by lifetime
    # base_decay ≈ 1 / mean_lifetime
    "base_decay_estimate": 1.0 / 206
}


# -------------------------------
# Phase 4C — Structural & Growth Priors
# -------------------------------

DEGRADATION_STRUCTURE_PRIORS = {
    # One latent variable drives degradation
    "latent_health_variable": True,

    # Sensors degrade together, not independently
    "coupled_degradation": True,

    # Degradation accelerates near failure
    "growth_shape": "nonlinear_accelerating",

    # Noise is smaller than degradation trend
    "noise_to_signal_ratio": "low",

    # Early-life behavior is mostly flat
    "early_life_behavior": "stable"
}

# -------------------------------
# Phase 4D — Vibration Realism Priors
# (learned from real-world motor data)
# -------------------------------

VIBRATION_PRIORS = {
    # Baseline vibration always exists (healthy motors)
    "baseline_vibration": {
        "exists": True,
        "relative_level": "low",   # healthy RMS is small but non-zero
        "healthy_noise_std": "very_low"
    },

    # Growth behavior with damage
    "growth_behavior": {
        "shape": "strongly_nonlinear",
        "accelerates_near_failure": True,
        "intermediate_variability": True  # different fault types behave differently
    },

    # Noise characteristics
    "noise_characteristics": {
        "noise_present_when_healthy": True,
        "noise_increases_with_damage": True,
        "noise_to_signal_ratio": "low"  # signal dominates noise near failure
    },

    # Spike / impact behavior (from crest factor)
    "spike_behavior": {
        "spikes_exist": True,
        "spikes_are_rare": True,
        "spike_magnitude_relative_to_baseline": "high",
        "spike_magnitude_increases_with_damage": True,
        "spikes_affect_only": ["vibration"]
    },

    # Diagnostic importance
    "diagnostic_priority": {
        "primary_indicator": "vibration",
        "dominates_over": ["temperature", "current"],
        "earliest_failure_signal": True
    }
}
