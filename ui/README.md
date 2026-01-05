# 🏭 Industrial Predictive Maintenance Simulator - UI

**Phase 6: Real-Time Streaming & Digital Control Room**

## 🚀 Quick Start

```bash
# From project root
streamlit run ui/app.py
```

The app will open at `http://localhost:8501`

---

## 📁 Architecture

```
ui/
├── app.py                    # Main Streamlit application
├── simulator_manager.py      # State management & lifecycle
├── components/
│   ├── controls.py          # Control panel widgets
│   ├── charts.py            # Plotly visualizations
│   └── metrics.py           # KPI displays & status
└── README.md
```

---

## 🎮 Features Implemented

### ✅ Control Panel
- **Simulation Configuration**
  - Number of motors (1-20)
  - Degradation speed (0.1x-5.0x)
  - Sensor noise level (0-3x)
  - Load factor (0.5x-2.0x)
  - Alert threshold (10%-90%)

- **Playback Controls**
  - ▶️ **Play**: Start/resume simulation
  - ⏸️ **Pause**: Pause simulation
  - ⏹️ **Stop**: Stop completely
  - 🔄 **Restart**: Reset and restart

- **Manual Stepping**
  - +1, +10, +50, +100 timesteps

- **Auto-Run Mode**
  - Configurable steps per update
  - Adjustable refresh rate

### ✅ Motor Actions
- 💥 **Inject Failure**: Simulate sudden failure
- 🔧 **Maintenance**: Reset motor to healthy state

### ✅ Visualization Modes

#### 1. Dashboard View
- Live KPI metrics (total, healthy, warning, critical)
- Active alerts panel
- Real-time monitoring charts
- Motor health bars
- Fleet overview

#### 2. Detailed Analysis
- 4-panel sensor grid (temperature, vibration, current, RPM)
- Correlation heatmap
- Health vs sensor scatter plots

#### 3. Fleet Status
- Fleet statistics
- Health bar chart
- Detailed motor table

#### 4. Raw Data
- Historical sensor data
- Current motor status
- CSV export functionality

---

## 🏗️ Component Details

### `simulator_manager.py`
**Purpose**: Manages persistent simulator state

**Key Classes**:
- `SimulatorConfig`: Configuration dataclass
- `SimulatorState`: State enum (STOPPED, RUNNING, PAUSED)
- `SimulatorManager`: Main orchestrator

**Key Methods**:
- `initialize(config)`: Create factory simulator
- `step(num_steps)`: Advance simulation
- `pause()`, `resume()`, `stop()`, `restart()`: State control
- `inject_failure(motor_id)`: Inject failure
- `reset_motor(motor_id)`: Simulate maintenance
- `get_history_df()`: Get all history
- `get_motor_status()`: Get latest motor readings
- `get_alerts()`: Get critical motors
- `export_data(filepath)`: Save to CSV

### `components/controls.py`
**Purpose**: Interactive control widgets

**Functions**:
- `render_control_panel()`: Configuration sliders
- `render_simulation_controls()`: Play/pause/stop/step buttons
- `render_motor_actions()`: Failure injection & maintenance
- `render_export_controls()`: Data export

### `components/charts.py`
**Purpose**: Plotly visualization components

**Functions**:
- `plot_sensor_grid()`: 2×2 multi-sensor view
- `plot_health_bars()`: Horizontal health bars
- `plot_health_vs_sensor()`: Scatter plots
- `plot_correlation_heatmap()`: Sensor correlations
- `plot_realtime_dashboard()`: Compact live view

### `components/metrics.py`
**Purpose**: KPI displays and status

**Functions**:
- `render_kpi_metrics()`: Top-level metrics
- `render_alert_panel()`: Active alerts
- `render_motor_table()`: Detailed status table
- `render_simulation_info()`: Metadata
- `render_fleet_overview()`: Fleet statistics

---

## 🎯 Simulation States

| State | Description | Auto-Run |
|-------|-------------|----------|
| **STOPPED** | Simulation inactive | ❌ |
| **PAUSED** | Simulation paused, can step manually | ❌ |
| **RUNNING** | Simulation running automatically | ✅ |

---

## 📊 Data Flow

```
User Input → Controls → SimulatorManager → FactorySimulator
                                ↓
                          History Buffer
                                ↓
                    Charts ← DataFrame ← Manager
```

---

## 🎨 Design Principles

1. **Modularity**: Each component is self-contained
2. **Persistence**: Session state maintains simulator across reruns
3. **Responsiveness**: Charts update in real-time
4. **Scalability**: Handles 1-20 motors efficiently
5. **Professional**: Industrial-grade UI/UX

---

## 🔧 Configuration Options

### Recommended Settings

**Quick Demo**:
```
Motors: 5
Degradation: 2.0x
Noise: 1.0x
Load: 1.2x
Steps per update: 5
Refresh rate: 1.0s
```

**Long Run**:
```
Motors: 10
Degradation: 1.0x
Noise: 0.5x
Load: 1.0x
Steps per update: 10
Refresh rate: 0.5s
```

**Stress Test**:
```
Motors: 20
Degradation: 3.0x
Noise: 2.0x
Load: 1.8x
Steps per update: 20
Refresh rate: 0.2s
```

---

## 💡 Tips

- **Start with Initialize**: Always click "Initialize Simulator" before stepping
- **Use Play for Auto-Run**: Click Play to start continuous simulation
- **Pause to Inspect**: Pause to manually step and analyze
- **Export Before Reset**: Export data before restarting if you need it
- **Watch Alerts**: Critical alerts trigger at <30% health by default
- **Inject Failures**: Test your monitoring by injecting failures
- **Maintenance Events**: Simulate maintenance to see recovery

---

## 🐛 Troubleshooting

**App won't start**:
```bash
pip install streamlit plotly pandas
```

**"Factory not initialized"**:
- Click "Initialize Simulator" in sidebar

**Charts not updating**:
- Ensure you've clicked "Step" or "Play"
- Check if simulation is in STOPPED state

**High memory usage**:
- Reduce `max_history` in `SimulatorConfig`
- Lower number of motors
- Export and restart periodically

---

## 🚦 Next Steps

### Phase 7: Production Features
- [ ] Kafka/Redpanda streaming
- [ ] Database persistence (InfluxDB)
- [ ] WebSocket real-time updates
- [ ] Multi-user support
- [ ] Authentication
- [ ] Cloud deployment (Azure/AWS)
- [ ] Grafana integration
- [ ] ML model inference integration
- [ ] Anomaly detection overlay
- [ ] Predictive maintenance alerts

---

## 📚 Related Files

- `simulator/factory.py`: Multi-motor simulation
- `simulator/motor.py`: Single motor physics
- `simulator/config_realistic.py`: Calibrated parameters
- `notebooks/phase1_test.ipynb`: Testing & validation

---

Built with ❤️ using **Streamlit** + **Physics-Based Modeling**
