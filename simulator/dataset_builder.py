import numpy as np
import pandas as pd

def build_supervised_dataset(
    df,
    sensor_cols,
    window_size=30,
    horizon=25,
    health_col="bearing_health",
    motor_id_col="motor_id",
    time_col="time"
):
    """
    Build supervised ML dataset with perfectly aligned X, y, and metadata.
    """

    X, y, meta_rows = [], [], []

    for motor_id, motor_df in df.groupby(motor_id_col):
        motor_df = motor_df.sort_values(time_col).reset_index(drop=True)

        # Find failure time
        failed = motor_df[motor_df[health_col] <= 0]
        if failed.empty:
            continue

        failure_time = failed.iloc[0][time_col]

        for t in range(window_size - 1, len(motor_df)):
            current_time = motor_df.loc[t, time_col]

            # Stop at failure
            if current_time >= failure_time:
                break

            # Extract window
            start = t - window_size + 1
            end = t + 1
            window = motor_df.iloc[start:end][sensor_cols].values

            # Label
            label = int((failure_time - current_time) <= horizon)

            # Append ALL together
            X.append(window)
            y.append(label)
            meta_rows.append({
                "motor_id": motor_id,
                "time": current_time,
                "failure_time": failure_time,
                "label": label
            })

    X = np.array(X)
    y = np.array(y)
    meta_df = pd.DataFrame(meta_rows)

    return X, y, meta_df
