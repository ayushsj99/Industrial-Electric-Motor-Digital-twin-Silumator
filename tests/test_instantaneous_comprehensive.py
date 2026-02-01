"""
Comprehensive Test Suite for Instantaneous Mode
Tests all aspects: physics, implementation, data quality, edge cases, performance
"""
import sys
import os
import time
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ui_path = os.path.join(project_root, 'ui')
for path in [project_root, ui_path]:
    if path not in sys.path:
        sys.path.append(path)

from ui.simulator_manager import SimulatorManager, SimulatorConfig
from simulator.state import HealthState, DegradationStage


class InstantaneousTestSuite:
    """Comprehensive test suite for instantaneous mode"""
    
    def __init__(self):
        self.test_results = []
        self.failures = []
        
    def log_test(self, test_name: str, passed: bool, details: str = ""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        
        if not passed:
            self.failures.append(test_name)
    
    def test_basic_configuration(self) -> bool:
        """Test 1: Basic configuration handling"""
        try:
            config = SimulatorConfig(
                num_motors=2,
                generation_mode="instantaneous",
                target_maintenance_cycles=1,
                warning_threshold=0.5,
                critical_threshold=0.3
            )
            
            manager = SimulatorManager()
            manager.initialize(config)
            
            # Verify configuration
            assert manager.config.num_motors == 2
            assert manager.config.generation_mode == "instantaneous"
            assert manager.config.target_maintenance_cycles == 1
            assert len(manager.factory.motors) == 2
            
            return True
        except Exception as e:
            self.log_test("Basic Configuration", False, f"Exception: {e}")
            return False
    
    def test_motor_diversity(self) -> bool:
        """Test 2: Motor diversity and individual characteristics"""
        try:
            config = SimulatorConfig(num_motors=10, generation_mode="instantaneous")
            manager = SimulatorManager()
            manager.initialize(config)
            
            # Check motor characteristics diversity
            load_factors = [m.state.load_factor for m in manager.factory.motors]
            lifespans = [m.state.target_hours_to_critical for m in manager.factory.motors]
            stage1_exps = [m.state.stage_1_power_exponent for m in manager.factory.motors]
            initial_healths = [m.state.motor_health for m in manager.factory.motors]
            
            # Verify diversity
            load_factor_range = max(load_factors) - min(load_factors)
            lifespan_range = max(lifespans) - min(lifespans)
            exp_range = max(stage1_exps) - min(stage1_exps)
            health_range = max(initial_healths) - min(initial_healths)
            
            diversity_checks = [
                ("Load factor diversity", load_factor_range > 0.1),
                ("Lifespan diversity", lifespan_range > 500),  # Should span 1000-3000 hours
                ("Degradation curve diversity", exp_range > 1.0),  # Should span 1.5-3.5
                ("Initial health diversity", health_range > 0.005)
            ]
            
            all_diverse = all(check[1] for check in diversity_checks)
            details = "; ".join([f"{name}: {check}" for name, check in diversity_checks])
            
            return all_diverse, details
        except Exception as e:
            return False, f"Exception: {e}"
    
    def test_single_motor_single_cycle(self) -> Tuple[bool, str]:
        """Test 3: Simplest case - 1 motor, 1 cycle"""
        try:
            config = SimulatorConfig(
                num_motors=1,
                target_maintenance_cycles=1,
                generation_mode="instantaneous"
            )
            
            manager = SimulatorManager()
            manager.initialize(config)
            
            result_df = manager.generate_until_all_critical()
            
            # Verify basic structure
            checks = [
                ("Has data", len(result_df) > 0),
                ("Single motor", result_df['motor_id'].nunique() == 1),
                ("Single cycle", result_df['cycle_id'].nunique() == 1),
                ("Motor 0 exists", 0 in result_df['motor_id'].values),
                ("Cycle 0 exists", 0 in result_df['cycle_id'].values),
                ("Has maintenance event", result_df['maintenance_event'].notna().any()),
                ("Health progression", result_df['motor_health'].min() < 0.5)  # Should reach low health
            ]
            
            all_passed = all(check[1] for check in checks)
            details = "; ".join([f"{name}: {check}" for name, check in checks])
            
            return all_passed, details
        except Exception as e:
            return False, f"Exception: {e}"
    
    def test_multi_motor_multi_cycle(self) -> Tuple[bool, str]:
        """Test 4: Complex case - multiple motors, multiple cycles"""
        try:
            config = SimulatorConfig(
                num_motors=3,
                target_maintenance_cycles=2,
                generation_mode="instantaneous"
            )
            
            manager = SimulatorManager()
            manager.initialize(config)
            
            result_df = manager.generate_until_all_critical()
            
            # Verify structure
            motor_ids = sorted(result_df['motor_id'].unique())
            cycle_ids = sorted(result_df['cycle_id'].unique())
            
            checks = [
                ("Correct motors", motor_ids == [0, 1, 2]),
                ("Correct cycles", cycle_ids == [0, 1]),
                ("All combinations", len(result_df[['motor_id', 'cycle_id']].drop_duplicates()) == 6),
                ("Has maintenance", result_df['maintenance_event'].notna().sum() >= 6),  # At least one per combination
                ("Reasonable data size", 10000 < len(result_df) < 200000)
            ]
            
            all_passed = all(check[1] for check in checks)
            details = "; ".join([f"{name}: {check}" for name, check in checks])
            
            return all_passed, details
        except Exception as e:
            return False, f"Exception: {e}"
    
    def test_physics_correctness(self) -> Tuple[bool, str]:
        """Test 5: Physics and degradation correctness"""
        try:
            config = SimulatorConfig(
                num_motors=2,
                target_maintenance_cycles=1,
                generation_mode="instantaneous"
            )
            
            manager = SimulatorManager()
            manager.initialize(config)
            
            result_df = manager.generate_until_all_critical()
            
            physics_checks = []
            
            # Check each motor's degradation pattern
            for motor_id in result_df['motor_id'].unique():
                motor_data = result_df[result_df['motor_id'] == motor_id].copy()
                motor_data = motor_data.sort_values('time')
                
                # Health should generally decrease (allowing for noise)
                health_trend = motor_data['motor_health'].iloc[-100:].mean() < motor_data['motor_health'].iloc[:100].mean()
                physics_checks.append((f"Motor {motor_id} health decreases", health_trend))
                
                # Should start healthy and end critical
                starts_healthy = motor_data['motor_health'].iloc[0] > 0.8
                ends_critical = motor_data['motor_health'].min() < 0.4
                physics_checks.append((f"Motor {motor_id} starts healthy", starts_healthy))
                physics_checks.append((f"Motor {motor_id} reaches critical", ends_critical))
                
                # Should have realistic sensor values
                temp_realistic = (motor_data['temperature'].min() > 10) and (motor_data['temperature'].max() < 200)
                vib_realistic = (motor_data['vibration'].min() >= -5) and (motor_data['vibration'].max() < 15)  # Fixed: realistic vibration range
                current_realistic = (motor_data['current'].min() > 0) and (motor_data['current'].max() < 100)
                
                physics_checks.append((f"Motor {motor_id} temperature realistic", temp_realistic))
                physics_checks.append((f"Motor {motor_id} vibration realistic", vib_realistic))
                physics_checks.append((f"Motor {motor_id} current realistic", current_realistic))
            
            all_physics_correct = all(check[1] for check in physics_checks)
            details = "; ".join([f"{name}: {check}" for name, check in physics_checks[:5]])  # Show first 5
            
            return all_physics_correct, details
        except Exception as e:
            return False, f"Exception: {e}"
    
    def test_data_structure_integrity(self) -> Tuple[bool, str]:
        """Test 6: Data structure and column integrity"""
        try:
            config = SimulatorConfig(
                num_motors=2,
                target_maintenance_cycles=2,
                generation_mode="instantaneous"
            )
            
            manager = SimulatorManager()
            manager.initialize(config)
            
            result_df = manager.generate_until_all_critical()
            
            # Check required columns
            required_cols = [
                'motor_id', 'cycle_id', 'time', 'motor_health', 'temperature',
                'vibration', 'current', 'rpm', 'health_state', 'degradation_stage',
                'regime', 'maintenance_event'
            ]
            
            # Check that time is sequential within each motor (global timeline approach)
            time_sequential_per_motor = all(
                group['time'].is_monotonic_increasing 
                for motor_id, group in result_df.groupby('motor_id')
            )
            
            structure_checks = [
                ("Has all required columns", all(col in result_df.columns for col in required_cols)),
                ("No null motor_ids", result_df['motor_id'].notna().all()),
                ("No null cycle_ids", result_df['cycle_id'].notna().all()),
                ("No null times", result_df['time'].notna().all()),
                ("No null health", result_df['motor_health'].notna().all()),
                ("Time is sequential per motor", time_sequential_per_motor),
                ("Health in valid range", (result_df['motor_health'] >= 0).all() and (result_df['motor_health'] <= 1).all()),
                ("Motor IDs are integers", result_df['motor_id'].dtype in ['int64', 'int32']),
                ("Cycle IDs are integers", result_df['cycle_id'].dtype in ['int64', 'int32'])
            ]
            
            all_structure_good = all(check[1] for check in structure_checks)
            details = "; ".join([f"{name}: {check}" for name, check in structure_checks])
            
            return all_structure_good, details
        except Exception as e:
            return False, f"Exception: {e}"
    
    def test_maintenance_logic(self) -> Tuple[bool, str]:
        """Test 7: Maintenance and cycle completion logic"""
        try:
            config = SimulatorConfig(
                num_motors=2,
                target_maintenance_cycles=2,
                generation_mode="instantaneous"
            )
            
            manager = SimulatorManager()
            manager.initialize(config)
            
            result_df = manager.generate_until_all_critical()
            
            maintenance_checks = []
            
            # Check maintenance events per motor per cycle
            for motor_id in result_df['motor_id'].unique():
                for cycle_id in result_df['cycle_id'].unique():
                    motor_cycle_data = result_df[
                        (result_df['motor_id'] == motor_id) & 
                        (result_df['cycle_id'] == cycle_id)
                    ]
                    
                    has_maintenance = motor_cycle_data['maintenance_event'].notna().any()
                    maintenance_checks.append((f"Motor {motor_id} Cycle {cycle_id} has maintenance", has_maintenance))
                    
                    if len(motor_cycle_data) > 0:
                        # Health should reset after maintenance
                        maintenance_rows = motor_cycle_data[motor_cycle_data['maintenance_event'].notna()]
                        if len(maintenance_rows) > 0:
                            last_maintenance_idx = maintenance_rows.index[-1]
                            if last_maintenance_idx < motor_cycle_data.index[-1]:
                                # There's data after maintenance
                                health_after_maintenance = motor_cycle_data.loc[last_maintenance_idx + 1:, 'motor_health'].iloc[0] if len(motor_cycle_data.loc[last_maintenance_idx + 1:]) > 0 else None
                                if health_after_maintenance is not None:
                                    health_reset = health_after_maintenance > 0.8
                                    maintenance_checks.append((f"Motor {motor_id} health resets after maintenance", health_reset))
            
            all_maintenance_correct = all(check[1] for check in maintenance_checks)
            details = f"Checked {len(maintenance_checks)} maintenance scenarios"
            
            return all_maintenance_correct, details
        except Exception as e:
            return False, f"Exception: {e}"
    
    def test_edge_cases(self) -> Tuple[bool, str]:
        """Test 8: Edge cases and boundary conditions"""
        edge_cases = []
        
        try:
            # Edge case 1: Maximum motors
            config_max = SimulatorConfig(num_motors=20, target_maintenance_cycles=1, generation_mode="instantaneous")
            manager_max = SimulatorManager()
            manager_max.initialize(config_max)
            result_max = manager_max.generate_until_all_critical()
            
            edge_cases.append(("Max motors (20) works", len(result_max) > 0 and result_max['motor_id'].nunique() == 20))
            
        except Exception as e:
            edge_cases.append(("Max motors (20) works", False))
        
        try:
            # Edge case 2: Maximum cycles
            config_cycles = SimulatorConfig(num_motors=2, target_maintenance_cycles=5, generation_mode="instantaneous")
            manager_cycles = SimulatorManager()
            manager_cycles.initialize(config_cycles)
            result_cycles = manager_cycles.generate_until_all_critical()
            
            edge_cases.append(("Max cycles (5) works", result_cycles['cycle_id'].nunique() == 5))
            
        except Exception as e:
            edge_cases.append(("Max cycles (5) works", False))
        
        try:
            # Edge case 3: Custom thresholds
            config_thresh = SimulatorConfig(
                num_motors=1, 
                target_maintenance_cycles=1, 
                generation_mode="instantaneous",
                warning_threshold=0.6,
                critical_threshold=0.1
            )
            manager_thresh = SimulatorManager()
            manager_thresh.initialize(config_thresh)
            result_thresh = manager_thresh.generate_until_all_critical()
            
            edge_cases.append(("Custom thresholds work", len(result_thresh) > 0))
            
        except Exception as e:
            edge_cases.append(("Custom thresholds work", False))
        
        all_edge_cases_pass = all(check[1] for check in edge_cases)
        details = "; ".join([f"{name}: {check}" for name, check in edge_cases])
        
        return all_edge_cases_pass, details
    
    def test_performance_and_memory(self) -> Tuple[bool, str]:
        """Test 9: Performance and memory usage"""
        try:
            config = SimulatorConfig(
                num_motors=5,
                target_maintenance_cycles=2,
                generation_mode="instantaneous"
            )
            
            manager = SimulatorManager()
            manager.initialize(config)
            
            # Time the generation
            start_time = time.time()
            result_df = manager.generate_until_all_critical()
            end_time = time.time()
            
            execution_time = end_time - start_time
            data_size = len(result_df)
            
            performance_checks = [
                ("Reasonable execution time", execution_time < 90),  # Allow up to 90 seconds for large datasets
                ("Reasonable data size", 10000 < data_size < 500000),  # Between 10K and 500K records
                ("Data stored in history", len(manager.history) == data_size),  # History management working
                ("Consistent performance", data_size / execution_time > 2000)  # Should generate >2000 records/second
            ]
            
            all_performance_good = all(check[1] for check in performance_checks)
            details = f"Time: {execution_time:.1f}s, Size: {data_size} records"
            
            return all_performance_good, details
        except Exception as e:
            return False, f"Exception: {e}"
    
    def test_data_export_compatibility(self) -> Tuple[bool, str]:
        """Test 10: Data export and analysis compatibility"""
        try:
            config = SimulatorConfig(
                num_motors=3,
                target_maintenance_cycles=1,
                generation_mode="instantaneous"
            )
            
            manager = SimulatorManager()
            manager.initialize(config)
            
            result_df = manager.generate_until_all_critical()
            
            # Test common data analysis operations
            export_checks = []
            
            # Groupby operations
            try:
                grouped = result_df.groupby(['motor_id', 'cycle_id'])['motor_health'].mean()
                export_checks.append(("Groupby works", len(grouped) > 0))
            except:
                export_checks.append(("Groupby works", False))
            
            # Pivot operations
            try:
                pivot = result_df.pivot_table(values='motor_health', index='time', columns='motor_id', aggfunc='mean')
                export_checks.append(("Pivot works", pivot.shape[0] > 0))
            except:
                export_checks.append(("Pivot works", False))
            
            # CSV export
            try:
                csv_string = result_df.to_csv()
                export_checks.append(("CSV export works", len(csv_string) > 1000))
            except:
                export_checks.append(("CSV export works", False))
            
            # Statistical analysis
            try:
                correlations = result_df[['motor_health', 'temperature', 'vibration', 'current']].corr()
                export_checks.append(("Correlation analysis works", correlations.shape == (4, 4)))
            except:
                export_checks.append(("Correlation analysis works", False))
            
            all_export_compatible = all(check[1] for check in export_checks)
            details = "; ".join([f"{name}: {check}" for name, check in export_checks])
            
            return all_export_compatible, details
        except Exception as e:
            return False, f"Exception: {e}"
    
    def run_all_tests(self):
        """Run all tests and report results"""
        print("🧪 COMPREHENSIVE INSTANTANEOUS MODE TEST SUITE")
        print("=" * 60)
        
        # Define all tests
        tests = [
            ("Basic Configuration", self.test_basic_configuration),
            ("Motor Diversity", self.test_motor_diversity),
            ("Single Motor Single Cycle", self.test_single_motor_single_cycle),
            ("Multi Motor Multi Cycle", self.test_multi_motor_multi_cycle),
            ("Physics Correctness", self.test_physics_correctness),
            ("Data Structure Integrity", self.test_data_structure_integrity),
            ("Maintenance Logic", self.test_maintenance_logic),
            ("Edge Cases", self.test_edge_cases),
            ("Performance and Memory", self.test_performance_and_memory),
            ("Data Export Compatibility", self.test_data_export_compatibility)
        ]
        
        # Run each test
        for test_name, test_func in tests:
            print(f"\n📋 Running: {test_name}")
            try:
                if test_name == "Basic Configuration":
                    result = test_func()
                    passed = result
                    details = ""
                else:
                    passed, details = test_func()
                
                self.log_test(test_name, passed, details)
            except Exception as e:
                self.log_test(test_name, False, f"Test crashed: {e}")
        
        # Summary
        print(f"\n{'=' * 60}")
        print("📊 TEST SUMMARY")
        print(f"{'=' * 60}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
        
        if self.failures:
            print(f"\n🔍 FAILED TESTS:")
            for failure in self.failures:
                print(f"  • {failure}")
        
        if passed_tests == total_tests:
            print(f"\n🎉 ALL TESTS PASSED! Instantaneous mode is fully functional.")
        else:
            print(f"\n⚠️  Some tests failed. Review the failures above.")
        
        return passed_tests == total_tests


def main():
    """Run the comprehensive test suite"""
    # Suppress warnings for cleaner output
    warnings.filterwarnings('ignore')
    
    suite = InstantaneousTestSuite()
    suite.run_all_tests()


if __name__ == "__main__":
    main()