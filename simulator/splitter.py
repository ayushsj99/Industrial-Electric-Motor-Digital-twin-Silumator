import numpy as np

def split_by_motor(
    X,
    y,
    meta_df,
    motor_id_col="motor_id",
    random_state=42
):
    """
    Robust motor-wise split.
    - Works for small fleets (>=3 motors)
    - Guarantees non-empty train/val/test
    """

    rng = np.random.default_rng(random_state)

    motor_ids = meta_df[motor_id_col].unique()
    n_motors = len(motor_ids)

    if n_motors < 3:
        raise ValueError("Need at least 3 motors for train/val/test split.")

    # Shuffle motors
    motor_ids = rng.permutation(motor_ids)

    # For small fleets, use count-based split
    if n_motors <= 10:
        n_train = max(1, int(0.6 * n_motors))
        n_val = 1
        n_test = n_motors - n_train - n_val
        if n_test < 1:
            n_test = 1
            n_train -= 1
    else:
        # For larger fleets, percentage-based split
        n_train = int(0.7 * n_motors)
        n_val = int(0.15 * n_motors)
        n_test = n_motors - n_train - n_val

    train_motors = motor_ids[:n_train]
    val_motors = motor_ids[n_train:n_train + n_val]
    test_motors = motor_ids[n_train + n_val:]

    def subset(motor_set):
        idx = meta_df[motor_id_col].isin(motor_set).values
        return X[idx], y[idx], meta_df[idx]

    return {
        "train": subset(train_motors),
        "val": subset(val_motors),
        "test": subset(test_motors)
    }
