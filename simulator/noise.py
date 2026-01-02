import numpy as np


def add_gaussian_noise(value, std):
    """
    Add zero-mean Gaussian noise to a sensor reading.
    """
    return value + np.random.normal(0, std)


def add_spike(value, probability, spike_magnitude):
    """
    Occasionally inject a spike into the signal.
    """
    if np.random.rand() < probability:
        return value + spike_magnitude * np.random.choice([-1, 1])
    return value


def maybe_drop(value, drop_prob):
    """
    Randomly drop a sensor reading (simulate missing data).
    """
    if np.random.rand() < drop_prob:
        return None
    return value
