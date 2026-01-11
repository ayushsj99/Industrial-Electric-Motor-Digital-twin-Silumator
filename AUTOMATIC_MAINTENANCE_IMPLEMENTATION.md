# Automatic Maintenance Labeling - Implementation Summary

## Overview
Added automatic maintenance scheduling and labeling when motors enter critical state with health < 0.30 (30%).

## Implementation Details

### Key Changes in `simulator/factory.py`

#### 1. Added State Tracking (Lines 86-91)
```python
# Track automatic maintenance scheduling
# Key: motor_id, Value: scheduled timestep for maintenance
self.scheduled_automatic_maintenance = {}
# Track previous health state to detect entry into critical
self.previous_health_states = {}
```

#### 2. Modified Step Logic (Lines ~202-235)
```python
# Detect transition into critical state
if (prev_state != HealthState.CRITICAL and 
    current_state == HealthState.CRITICAL and 
    motor_id not in self.scheduled_automatic_maintenance):
    # Schedule maintenance randomly within 1 day (24 hours = 288 timesteps)
    delay = np.random.randint(1, 289)  # 1 to 288 timesteps
    self.scheduled_automatic_maintenance[motor_id] = self.time + delay

# Check for scheduled automatic maintenance
if (motor_id in self.scheduled_automatic_maintenance and 
    self.time >= self.scheduled_automatic_maintenance[motor_id] and
    motor.state.motor_health < 0.30):  # Only if health < 30%
    # Perform automatic maintenance
    self._perform_automatic_maintenance(motor)
    automatic_maintenance_occurred = True
    del self.scheduled_automatic_maintenance[motor_id]
```

#### 3. Updated Labeling (Lines ~267-275)
```python
# Label maintenance events (prioritize automatic over scheduled)
if automatic_maintenance_occurred:
    sensors["maintenance_event"] = "automatic_maintenance"
else:
    sensors["maintenance_event"] = maintenance_type
```

## Behavior

### Trigger Conditions
1. **Critical State Entry**: Motor health drops below 0.40 (40%) → Health State = "Critical"
2. **Scheduling**: Upon entering critical, random delay scheduled between 1-288 timesteps (5 min - 24 hours)
3. **Execution**: At scheduled time, IF health < 0.30 (30%), automatic maintenance executes

### What Happens During Maintenance
- Health reset to ~0.93-0.95 (like new)
- Hours since maintenance reset to 0
- New random lifespan generated (1000-3000 hours)
- New three-stage durations regenerated
- New power exponent sampled for Stage 1
- Physical degradation partially reset (misalignment, friction)

### Label in Data
- **Field**: `maintenance_event`
- **Value**: `"automatic_maintenance"` (when occurs)
- **Value**: `None` or scheduled maintenance type (when doesn't occur)

## Test Results

From `test_maintenance_labeling.py`:

```
Motor entered Critical at Step 21926 (health: 0.005)
Automatic Maintenance occurred at Step 22203 (health: 0.283)
Delay: 277 steps (23.1 hours) ✓ Within 24 hours
Health after: 0.947 (reset successful)
Label: 'automatic_maintenance' ✓
```

## Key Features

1. **Random Delay**: Maintenance doesn't happen immediately - occurs randomly within 24 hours
2. **Health Threshold**: Only executes if health < 0.30 at scheduled time
3. **Proper Labeling**: Now explicitly labeled as "automatic_maintenance" in data
4. **No Conflicts**: Automatic maintenance takes priority over scheduled maintenance in labeling
5. **Complete Reset**: Full lifecycle reset (unlike scheduled maintenance which just improves health)

## Data Output Format

Each record now contains:
```python
{
    ...
    "motor_health": float,  # 0-1 scale
    "health_state": str,    # "Healthy"/"Warning"/"Critical"
    "maintenance_event": str,  # "automatic_maintenance" / "lubrication" / "component_replacement" / None
    "hours_since_maintenance": float,  # Resets to 0 after automatic maintenance
    ...
}
```

## Use Cases for ML

This labeling enables:
1. **Survival Analysis**: Time-to-maintenance prediction
2. **Anomaly Detection**: Identify unusual degradation patterns before maintenance
3. **Maintenance Scheduling**: Learn optimal maintenance timing
4. **Cost Optimization**: Balance maintenance costs vs failure costs
5. **Transfer Learning**: Separate pre/post maintenance data for better models

## Configuration

Default thresholds:
- **Critical State**: health < 0.40 (40%) - defined in `simulator/config.py`
- **Maintenance Trigger**: health < 0.30 (30%) - hardcoded in `factory.py`
- **Delay Range**: 1-288 timesteps (5 min - 24 hours) - hardcoded in `factory.py`

To modify:
```python
# In factory.py, line ~218
delay = np.random.randint(1, 289)  # Change range here

# In factory.py, line ~225
motor.state.motor_health < 0.30  # Change threshold here
```
