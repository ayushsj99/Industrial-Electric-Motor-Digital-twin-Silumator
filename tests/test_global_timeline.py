"""
Test the new synchronized global timeline implementation
"""
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ui_path = os.path.join(project_root, 'ui')
for path in [project_root, ui_path]:
    if path not in sys.path:
        sys.path.append(path)

from ui.simulator_manager import SimulatorManager, SimulatorConfig
import pandas as pd

def test_global_timeline():
    # Create a test with 3 motors, 1 cycle each
    config = SimulatorConfig(
        num_motors=3,
        target_maintenance_cycles=1,
        generation_mode='instantaneous',
        degradation_speed=5.0
    )

    manager = SimulatorManager()
    manager.initialize(config)

    # Generate synchronized data
    df = manager.generate_until_all_critical()

    # Analyze the global timeline
    print('\n📊 GLOBAL TIMELINE ANALYSIS:')
    print(f'Total records: {len(df)}')
    print(f'Time range: {df["time"].min():.1f} to {df["time"].max():.1f}')

    # Check if motors start at the same time
    motor_start_times = df.groupby('motor_id')['time'].min()
    print('\nMotor start times:')
    for motor_id, start_time in motor_start_times.items():
        print(f'  Motor {motor_id}: starts at time {start_time:.1f}')

    # Check simultaneous operation
    time_0_motors = df[df['time'] == 0]['motor_id'].unique()
    print(f'\nMotors active at time 0: {sorted(time_0_motors)}')
    
    all_start_same = all(start_time == 0.0 for start_time in motor_start_times)
    print(f'All motors start at time 0: {all_start_same}')

    # Sample timeline view
    print('\nFirst 10 timesteps:')
    sample_df = df[df['time'] <= 10].groupby('time')['motor_id'].apply(list).head(10)
    for time, motors in sample_df.items():
        print(f'  Time {time:.1f}: Motors {sorted(motors)}')
    
    # Check for gaps in motor operation
    print('\nMotor operation continuity:')
    for motor_id in df['motor_id'].unique():
        motor_data = df[df['motor_id'] == motor_id].sort_values('time')
        time_gaps = motor_data['time'].diff().dropna()
        max_gap = time_gaps.max() if len(time_gaps) > 0 else 0
        print(f'  Motor {motor_id}: Max time gap = {max_gap:.1f} (should be ≤1.0)')

if __name__ == "__main__":
    test_global_timeline()