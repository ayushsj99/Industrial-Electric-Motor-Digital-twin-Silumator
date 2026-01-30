"""Quick performance validation"""
import sys, os

project_root = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(project_root, 'ui')
for path in [project_root, ui_path]:
    if path not in sys.path:
        sys.path.append(path)

from test_instantaneous_comprehensive import InstantaneousTestSuite

print('🚀 FINAL PERFORMANCE VALIDATION')
print('=' * 40)

suite = InstantaneousTestSuite()
passed, details = suite.test_performance_and_memory()
print(f'Performance Test: {"✅ PASS" if passed else "❌ FAIL"} - {details}')