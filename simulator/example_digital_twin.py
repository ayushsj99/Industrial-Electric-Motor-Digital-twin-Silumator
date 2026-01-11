"""
Example usage and visualization of the Motor Digital Twin.
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from digital_twin import MotorDigitalTwin, simulate_fleet


def plot_single_motor_lifecycle(motor_id: str = "M001", random_state: int = 42):
    """Plot complete lifecycle of a single motor."""
    
    # Create motor instance
    twin = MotorDigitalTwin(motor_id=motor_id, random_state=random_state)
    
    # Simulate until failure
    df = twin.simulate(duration_hours=twin.T_total, dt=1.0)
    
    # Create figure with subplots
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))
    fig.suptitle(f'Motor {motor_id} - Complete Lifecycle ({twin.T_total:.0f} hours)', 
                 fontsize=14, fontweight='bold')
    
    # Plot 1: True vs Measured Health
    ax = axes[0, 0]
    ax.plot(df['time_hours'], df['H_true'], label='H_true (ground truth)', linewidth=2)
    ax.plot(df['time_hours'], df['H_meas'], label='H_meas (from sensors)', 
            linewidth=2, alpha=0.7)
    ax.axvline(twin.t1, color='green', linestyle='--', alpha=0.5, label='Stage 0→1')
    ax.axvline(twin.t2, color='orange', linestyle='--', alpha=0.5, label='Stage 1→2')
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Health Index')
    ax.set_title('Health Degradation')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 2: Vibration RMS
    ax = axes[0, 1]
    ax.plot(df['time_hours'], df['rms_vib'], color='red', linewidth=1.5)
    ax.axhline(twin.RMS_healthy, color='green', linestyle='--', alpha=0.5, label='Healthy')
    ax.axhline(twin.RMS_failure, color='red', linestyle='--', alpha=0.5, label='Failure')
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('RMS (m/s²)')
    ax.set_title('Vibration RMS')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 3: Temperature
    ax = axes[1, 0]
    ax.plot(df['time_hours'], df['temp_c'], color='orange', linewidth=1.5)
    ax.axhline(twin.T_baseline, color='green', linestyle='--', alpha=0.5, label='Baseline')
    ax.axhline(twin.T_crit, color='red', linestyle='--', alpha=0.5, label='Critical')
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Temperature (°C)')
    ax.set_title('Bearing Temperature')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # Plot 4: Kurtosis
    ax = axes[1, 1]
    ax.plot(df['time_hours'], df['kurt_vib'], color='purple', linewidth=1.5)
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('Kurtosis')
    ax.set_title('Vibration Kurtosis')
    ax.grid(True, alpha=0.3)
    
    # Plot 5: THD
    ax = axes[2, 0]
    ax.plot(df['time_hours'], df['thd'] * 100, color='brown', linewidth=1.5)
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('THD (%)')
    ax.set_title('Current THD')
    ax.grid(True, alpha=0.3)
    
    # Plot 6: RPM
    ax = axes[2, 1]
    ax.plot(df['time_hours'], df['rpm'], color='blue', linewidth=1.5)
    ax.axhline(twin.rated_rpm, color='green', linestyle='--', alpha=0.5, label='Rated')
    ax.set_xlabel('Time (hours)')
    ax.set_ylabel('RPM')
    ax.set_title('Motor Speed')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'motor_{motor_id}_lifecycle.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    return df


def plot_fleet_comparison(num_motors: int = 5, duration_hours: float = 2000):
    """Plot health trajectories for multiple motors."""
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 8))
    fig.suptitle(f'Fleet of {num_motors} Motors - Variability', 
                 fontsize=14, fontweight='bold')
    
    for i in range(num_motors):
        motor_id = f"M{i+1:03d}"
        twin = MotorDigitalTwin(motor_id=motor_id, random_state=42 + i)
        df = twin.simulate(duration_hours=min(duration_hours, twin.T_total), dt=1.0)
        
        # Plot true health
        axes[0].plot(df['time_hours'], df['H_true'], label=motor_id, linewidth=2, alpha=0.7)
        
        # Plot vibration RMS
        axes[1].plot(df['time_hours'], df['rms_vib'], label=motor_id, linewidth=2, alpha=0.7)
    
    axes[0].set_xlabel('Time (hours)')
    axes[0].set_ylabel('H_true')
    axes[0].set_title('True Health Index - Unit-to-Unit Variability')
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)
    
    axes[1].set_xlabel('Time (hours)')
    axes[1].set_ylabel('RMS (m/s²)')
    axes[1].set_title('Vibration RMS - Unit-to-Unit Variability')
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('fleet_comparison.png', dpi=150, bbox_inches='tight')
    plt.show()


def analyze_sensor_correlations(motor_id: str = "M001", random_state: int = 42):
    """Analyze correlations between sensors and true health."""
    
    twin = MotorDigitalTwin(motor_id=motor_id, random_state=random_state)
    df = twin.simulate(duration_hours=twin.T_total, dt=1.0)
    
    # Compute correlations
    sensors = ['rms_vib', 'kurt_vib', 'crest_vib', 'temp_c', 'thd', 'rpm']
    correlations = {sensor: df[sensor].corr(df['H_true']) for sensor in sensors}
    
    print(f"\n{'='*50}")
    print(f"Motor {motor_id} - Sensor Correlations with H_true")
    print(f"{'='*50}")
    for sensor, corr in sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True):
        print(f"{sensor:15s}: {corr:+.4f}")
    print(f"{'='*50}\n")
    
    # Create correlation plot
    fig, ax = plt.subplots(figsize=(10, 6))
    sensors_sorted = sorted(correlations.items(), key=lambda x: abs(x[1]), reverse=True)
    names = [s[0] for s in sensors_sorted]
    values = [s[1] for s in sensors_sorted]
    colors = ['red' if v > 0 else 'blue' for v in values]
    
    ax.barh(names, values, color=colors, alpha=0.7)
    ax.set_xlabel('Correlation with H_true')
    ax.set_title('Sensor Correlation Analysis')
    ax.axvline(0, color='black', linewidth=0.8)
    ax.grid(True, alpha=0.3, axis='x')
    
    plt.tight_layout()
    plt.savefig('sensor_correlations.png', dpi=150, bbox_inches='tight')
    plt.show()
    
    return correlations


def example_export_fleet_data():
    """Example: Generate and export fleet data to CSV."""
    
    print("Generating fleet data...")
    df = simulate_fleet(
        num_motors=10,
        duration_hours=2000,
        dt=1.0,
        random_state=42,
        output_dir='./fleet_data'
    )
    
    print(f"\nGenerated {len(df)} records")
    print(f"Motors: {df['motor_id'].nunique()}")
    print(f"\nSample data:")
    print(df.head(10))
    print(f"\nData saved to ./fleet_data/")


if __name__ == "__main__":
    print("Motor Digital Twin - Examples\n")
    
    # Example 1: Single motor lifecycle
    print("1. Plotting single motor lifecycle...")
    df = plot_single_motor_lifecycle(motor_id="M001", random_state=42)
    
    # Example 2: Fleet comparison
    print("\n2. Plotting fleet comparison...")
    plot_fleet_comparison(num_motors=5, duration_hours=2000)
    
    # Example 3: Correlation analysis
    print("\n3. Analyzing sensor correlations...")
    correlations = analyze_sensor_correlations(motor_id="M001", random_state=42)
    
    # Example 4: Export data
    print("\n4. Exporting fleet data...")
    example_export_fleet_data()
    
    print("\n✓ All examples completed!")
