"""
Diagnostic Tests for Failed Cases
"""
import sys
import os
import pandas as pd
import numpy as np

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(project_root, 'ui')
for path in [project_root, ui_path]:
    if path not in sys.path:
        sys.path.append(path)

from ui.simulator_manager import SimulatorManager, SimulatorConfig


def diagnose_physics_issue():
    """Diagnose the vibration realism issue"""
    print("🔍 DIAGNOSING PHYSICS ISSUE")
    print("=" * 40)
    
    config = SimulatorConfig(
        num_motors=1,
        target_maintenance_cycles=1,
        generation_mode="instantaneous"
    )
    
    manager = SimulatorManager()
    manager.initialize(config)
    result_df = manager.generate_until_all_critical()
    
    # Analyze sensor values
    print(f"📊 Sensor Value Analysis:")
    print(f"Temperature: {result_df['temperature'].min():.2f} - {result_df['temperature'].max():.2f}")
    print(f"Vibration:   {result_df['vibration'].min():.2f} - {result_df['vibration'].max():.2f}")
    print(f"Current:     {result_df['current'].min():.2f} - {result_df['current'].max():.2f}")
    print(f"RPM:         {result_df['rpm'].min():.2f} - {result_df['rpm'].max():.2f}")
    
    # Check for outliers
    vib_outliers = result_df[result_df['vibration'] > 50]
    print(f"\\n🚨 Vibration outliers (>50): {len(vib_outliers)} records")
    if len(vib_outliers) > 0:
        print(f"   Max vibration: {vib_outliers['vibration'].max():.2f}")
        print(f"   Health at max vib: {vib_outliers.loc[vib_outliers['vibration'].idxmax(), 'motor_health']:.3f}")
    
    # Check vibration vs health correlation
    correlation = result_df['vibration'].corr(result_df['motor_health'])
    print(f"\\n📈 Vibration-Health Correlation: {correlation:.3f}")
    print("   (Should be negative - higher vibration = lower health)")
    
    return result_df


def diagnose_performance_issue():
    """Diagnose the performance issue"""
    print("\\n🔍 DIAGNOSING PERFORMANCE ISSUE")
    print("=" * 40)
    
    import time
    
    # Test different sizes
    test_configs = [
        (1, 1, "Baseline"),
        (2, 1, "2 motors"),
        (3, 2, "Failed test config"),
        (5, 1, "5 motors 1 cycle"),
    ]
    
    for motors, cycles, description in test_configs:
        config = SimulatorConfig(
            num_motors=motors,
            target_maintenance_cycles=cycles,
            generation_mode="instantaneous"
        )
        
        manager = SimulatorManager()
        manager.initialize(config)
        
        start_time = time.time()
        result_df = manager.generate_until_all_critical()
        end_time = time.time()
        
        execution_time = end_time - start_time
        records_per_second = len(result_df) / execution_time if execution_time > 0 else 0
        
        print(f"{description}: {execution_time:.1f}s, {len(result_df)} records, {records_per_second:.0f} rec/sec")


def analyze_motor_variation():
    """Analyze motor-to-motor variation"""
    print("\\n🔍 MOTOR VARIATION ANALYSIS")
    print("=" * 40)
    
    config = SimulatorConfig(
        num_motors=5,
        target_maintenance_cycles=1,
        generation_mode="instantaneous"
    )
    
    manager = SimulatorManager()
    manager.initialize(config)
    result_df = manager.generate_until_all_critical()
    
    # Analyze variation by motor
    motor_stats = []
    for motor_id in sorted(result_df['motor_id'].unique()):
        motor_data = result_df[result_df['motor_id'] == motor_id]
        
        stats = {
            'motor_id': motor_id,
            'lifespan_steps': len(motor_data),
            'min_health': motor_data['motor_health'].min(),
            'max_health': motor_data['motor_health'].max(),
            'avg_temp': motor_data['temperature'].mean(),
            'max_vib': motor_data['vibration'].max(),
            'maintenance_events': motor_data['maintenance_event'].notna().sum()
        }
        motor_stats.append(stats)
    
    motor_df = pd.DataFrame(motor_stats)
    print("\\n📊 Motor Comparison:")
    print(motor_df.to_string(index=False, float_format='%.2f'))
    
    # Calculate variation coefficients
    lifespan_cv = motor_df['lifespan_steps'].std() / motor_df['lifespan_steps'].mean()
    temp_cv = motor_df['avg_temp'].std() / motor_df['avg_temp'].mean()
    
    print(f"\\n📈 Variation Analysis:")
    print(f"Lifespan Coefficient of Variation: {lifespan_cv:.3f}")
    print(f"Temperature Coefficient of Variation: {temp_cv:.3f}")
    print(f"Lifespan Range: {motor_df['lifespan_steps'].min()} - {motor_df['lifespan_steps'].max()} steps")
    
    return motor_df


def main():
    """Run all diagnostic tests"""
    print("🧪 DIAGNOSTIC TEST SUITE")
    print("=" * 50)
    
    # Run diagnostics
    physics_df = diagnose_physics_issue()
    diagnose_performance_issue()
    motor_variation_df = analyze_motor_variation()
    
    print(f"\\n✅ Diagnostics complete!")
    

if __name__ == "__main__":
    main()