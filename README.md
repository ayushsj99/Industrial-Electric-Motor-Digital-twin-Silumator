# 🏭 Industrial Predictive Maintenance Simulator  
*A Physics-Based Digital Twin for Realistic Motor Sensor Data*

[![Try it on Hugging Face](https://img.shields.io/badge/🤗-Try%20on%20Hugging%20Face-blue)](https://huggingface.co/spaces/ayushjadhav/industrial_data_simulator)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)

---

## 📌 Overview

**Generate realistic, ML-ready industrial motor sensor data in your browser!**

This physics-based digital twin simulates industrial electric motors with realistic degradation patterns, sensor responses, and maintenance events. Unlike synthetic datasets, this simulator models actual physical relationships between motor health and observable sensor readings.

**🚀 [Try it Now on Hugging Face →](https://huggingface.co/spaces/ayushjadhav/industrial_data_simulator)**

---

## ✨ Key Features

- **🔴 Live Mode**: Step-by-step simulation with real-time decision making
- **⚡ Batch Mode**: Generate complete datasets instantly  
- **📊 Realistic Physics**: Multi-stage degradation with proper sensor dynamics
- **🔧 Interactive Maintenance**: Make repair-or-replace decisions as motors degrade
- **📱 Web-Based**: No installation needed - runs in your browser
- **💾 Direct Download**: Export data straight to your computer

---

## 🎯 Perfect For

- **ML Researchers**: Benchmarking predictive maintenance algorithms
- **Data Scientists**: Training anomaly detection models
- **Students**: Learning about digital twins and industrial IoT
- **Engineers**: Prototyping maintenance strategies
- **Competitions**: Generating datasets for hackathons

---

## 🔬 What Gets Simulated

Each motor provides realistic time-series data:

| **Sensor** | **Unit** | **What It Represents** |
|------------|----------|------------------------|
| 🌡️ **Temperature** | °C | Frictional heating from bearing wear |
| 📳 **Vibration** | m/s² | Mechanical imbalances and defects |
| ⚡ **Current** | A | Electrical load from mechanical resistance |
| 🔄 **RPM** | rpm | Rotational speed affected by degradation |
| ❤️ **Motor Health** | 0-1 | True condition (ground truth for ML) |

---

## 🏗️ Degradation Physics

Motors follow a **realistic three-stage degradation**:

```
🟢 Healthy (70-85% of life)     →     🟡 Early Wear (12-22%)     →     🔴 Critical (5-10%)
   Stable operation                    Progressive deterioration           Rapid failure
   Minor fluctuations                  Power-law degradation              Exponential decay
```

**Key Realism Features:**
- Motors have different lifespans (1000-3000 hours)
- Sensor responses have physical delays (temperature lags, vibration immediate)
- Maintenance is imperfect and probabilistic
- No two motors degrade identically

---

## ⚙️ Simulation Modes

### 🔴 **Live Mode** (Interactive)
- Motors generate data step-by-step (5-minute intervals)
- When motors reach critical health, **you decide**: maintain or let fail
- Perfect for understanding degradation patterns
- Control degradation speed (1x to 5x faster)

### ⚡ **Batch Mode** (Dataset Generation)  
- Generate complete motor lifecycles instantly
- Automatic maintenance when motors reach critical levels
- Perfect for creating large ML datasets
- Set number of maintenance cycles per motor

---

## 📊 Validated Data Quality

✅ **Physically Realistic**: Sensor correlations match real industrial data  
✅ **ML-Ready**: No label leakage, proper train/test splits possible  
✅ **Statistically Valid**: Non-Gaussian distributions, realistic noise patterns  
✅ **Benchmarked**: Validated against NASA C-MAPSS dataset characteristics  

---

## 🚀 Quick Start Guide

### **Option 1: Use Online (Recommended)**

1. **🌐 [Open Hugging Face Space](https://huggingface.co/spaces/ayushjadhav/industrial_data_simulator)**
2. **⚙️ Configure**: Set number of motors, degradation speed, noise levels
3. **▶️ Start**: Choose Live mode for interaction or Batch mode for datasets  
4. **📊 Monitor**: Watch real-time dashboards and health metrics
5. **💾 Download**: Export CSV data directly to your computer

### **Option 2: Run Locally**

```bash
# Clone repository
git clone https://github.com/ayushsj99/industrial-predictive-maintenance-simulator
cd industrial-predictive-maintenance-simulator

# Install dependencies
pip install -r requirements.txt

# Run simulator
streamlit run ui/app.py
```

---

## 📖 How to Use

### **🔴 For Interactive Learning (Live Mode)**

1. Start with **3-5 motors** and **2x degradation speed**
2. Click **▶️ Play** to begin simulation  
3. Watch the dashboard - motors will show:
   - 🟢 Healthy (>70% health)
   - 🟡 Warning (30-70% health)  
   - 🔴 Critical (≤30% health)
4. When motors hit critical, decide: **🔧 Maintain** or **💥 Let Fail**
5. Export data when you have enough maintenance cycles

### **⚡ For Dataset Generation (Batch Mode)**

1. Set your desired **number of motors** (10-20 recommended)
2. Choose **maintenance cycles per motor** (1-3 cycles)
3. Click **⚡ Generate Data** and wait
4. Download the complete dataset as CSV
5. Use for ML training, analysis, or research

---

## 🔧 Configuration Options

| **Setting** | **Live Mode** | **Batch Mode** | **Description** |
|-------------|---------------|----------------|-----------------|
| **Motors** | 1-20 | 1-20 | Number of motors in factory |
| **Degradation Speed** | 0.1x-5x | N/A | How fast motors degrade |
| **Noise Level** | 0.1x-3x | 0.1x-3x | Sensor noise intensity |
| **Load Factor** | 0.5x-2x | 0.5x-2x | Operating load intensity |
| **Maintenance Cycles** | Auto | 1-10 | Complete degradation cycles |

---

## 📁 Dataset Schema

Downloaded CSV files contain these columns:

```
time                    # Simulation timestep (5-min intervals)
motor_id               # Unique motor identifier  
temperature            # Motor temperature (°C)
vibration              # Vibration RMS (m/s²)
current                # Electrical current (A)
rpm                    # Rotational speed (rpm)
motor_health           # True health state (0-1, ground truth)
health_state           # Categorical: HEALTHY/WARNING/CRITICAL
hours_since_maintenance # Operating hours since last maintenance
degradation_stage      # STAGE_0/STAGE_1/STAGE_2
maintenance_event      # Boolean: maintenance occurred this timestep
```

---

## 🎓 Educational Use Cases

### **For Students:**
- Learn about digital twins and Industry 4.0
- Understand sensor data patterns and correlations
- Practice ML on realistic industrial datasets

### **For Researchers:**
- Benchmark new predictive maintenance algorithms  
- Study the impact of different maintenance strategies
- Generate controlled datasets for academic papers

### **For Engineers:**
- Prototype maintenance decision systems
- Understand cost-benefit of different alert thresholds
- Train teams on data-driven maintenance concepts

---

## 🤝 Contributing

We welcome contributions! Areas for improvement:
- Additional sensor types (pressure, flow, etc.)
- Different machinery types (pumps, compressors)
- Advanced failure modes
- Maintenance cost modeling

---

## 📄 License

MIT License - free for academic and commercial use.

---

## 🔗 Links

- **🤗 [Try Online →](https://huggingface.co/spaces/ayushjadhav/industrial_data_simulator)**
- **📧 [GitHub Repository](https://github.com/ayushsj99/industrial-predictive-maintenance-simulator)**
- **📋 [Issues & Feedback](https://github.com/ayushsj99/industrial-predictive-maintenance-simulator/issues)**

---

**🎯 Ready to generate realistic industrial data? [Start here →](https://huggingface.co/spaces/ayushjadhav/industrial_data_simulator)**
