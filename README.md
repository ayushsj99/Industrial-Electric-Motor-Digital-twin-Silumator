---
title: Industrial Predictive Maintenance Simulator
emoji: 🏭
colorFrom: blue
colorTo: red
sdk: streamlit
sdk_version: 1.25.0
app_file: app.py
pinned: false
license: mit
tags:
- predictive-maintenance
- digital-twin
- simulation
- machine-learning
short_description: Physics-based digital twin for motor sensor data
---

# 🏭 Industrial Predictive Maintenance Simulator  
*A Physics-Based Digital Twin for ML-Ready Condition Monitoring Data*

---

## 📌 Overview

The **Industrial Predictive Maintenance Simulator** is a physics-based digital twin that generates **realistic, production-grade sensor data** for industrial electric motors operating in a factory environment.

Unlike simplistic simulators, this system explicitly models:

- Multi-stage mechanical degradation
- Physically-consistent sensor responses
- Asynchronous sensor dynamics (lagged response)
- Operating regime non-stationarity
- Imperfect sensors (noise, drift, dropouts)
- Probabilistic maintenance behavior

The resulting dataset is **validated for realism** and **ready for machine learning**, benchmarking, and research use.

---

## 🎯 Why This Project Exists

Real-world predictive maintenance data is:
- Expensive
- Proprietary
- Incomplete
- Noisy and difficult to label

This simulator provides:
- **Controlled realism**
- **Reproducible experiments**
- **Ground-truth health labels**
- **ML-ready degradation trajectories**

It is suitable for:
- Predictive maintenance model development
- RUL estimation research
- Anomaly detection benchmarking
- Educational demonstrations of digital twins

---

## 🧠 Core Design Philosophy

> **All observable sensor signals are causal functions of an unobserved latent health state.**

This ensures:
- Physical consistency
- Explainability
- Absence of label leakage
- Meaningful ML learning tasks

---

## 🏗️ System Architecture

industrial-predictive-maintenance-simulator/
├── simulator/ # Physics & degradation models
│ ├── motor.py
│ ├── digital_twin.py
│ ├── physics.py
│ ├── maintenance.py
│ ├── noise.py
│ └── sensor_imperfections.py
├── ui/ # Streamlit real-time dashboard
│ ├── app.py
│ └── components/
├── data/
│ ├── simulated/ # Generated datasets
│ └── validation/ # EDA & benchmarking artifacts
├── notebooks/ # Analysis & ML notebooks
└── README.md



---

## 🔬 Simulated Sensors

Each motor generates time-series data for:

| Sensor | Unit | Physical Basis |
|------|-----|----------------|
| Temperature | °C | Frictional heat + thermal inertia |
| Vibration (RMS) | m/s² | Bearing wear & misalignment |
| Current | A | Mechanical resistance & load |
| RPM | rpm | Slip due to degradation |
| Health (latent) | [0,1] | True internal condition |

---

## ⚙️ Degradation Model

The simulator follows a **three-stage degradation process**:

1. **Healthy Plateau**  
   - Minimal wear
   - Stable sensor readings

2. **Progressive Degradation**  
   - Power-law crack growth
   - Gradual sensor divergence

3. **Rapid Failure**  
   - Exponential health decay
   - Sharp sensor escalation

This mirrors the classic **bathtub curve** observed in industrial reliability engineering.

---

## 🛠️ Maintenance Modeling

Maintenance is **probabilistic and imperfect**, reflecting real-world behavior:

- Triggered near critical health
- Executed after random delay
- Partially resets degradation
- Never perfectly timed

Maintenance events are labeled but **do not leak future information**, preserving ML validity.

---

## 📊 Dataset Schema

Each record contains:

```text
temperature, vibration, current, rpm,
motor_health, health_state,
hours_since_maintenance,
degradation_stage,
time, motor_id,
operating_regime,
maintenance_event

## ✅ Data Validation & Benchmarking

This dataset has been rigorously validated using **Exploratory Data Analysis (EDA)** to confirm both **physical realism** and **machine-learning suitability**.

---

### 1️⃣ Missingness Validation

- Sensor dropouts: **0.4% – 0.7%**
- Missingness is **non-uniform** and **sensor-specific**
- Latent health variable is **always present**

✔ Matches real industrial telemetry behavior

---

### 2️⃣ Motor-to-Motor Variability

- Motors exhibit **different lifetimes**
- Motors degrade to **different minimum health levels**
- No identical or cloned asset trajectories

✔ Confirms **non-IID asset behavior**, a hallmark of real industrial fleets

---

### 3️⃣ Sensor Distribution Realism

- Sensor distributions are **non-Gaussian**
- **Right-skewed vibration** distributions
- **Long-tailed kurtosis**, indicating impulsive behavior
- **Tight RPM clustering** with gradual degradation drift

✔ Reflects physical constraints, wear dynamics, and measurement noise

---

### 4️⃣ Temporal & Causal Consistency

Cross-correlation analysis confirms **realistic sensor response lags**:

| Sensor       | Peak Correlation Lag |
|-------------|----------------------|
| Vibration   | 0–1 timesteps        |
| Current     | 4–6 timesteps        |
| Temperature | 15–20 timesteps      |

✔ Matches known physical response times (instantaneous, electrical inertia, thermal mass)

---

### 5️⃣ Correlation Structure

- Strong but **imperfect** correlations between sensors and health
- **RPM negatively correlated** with degradation
- No single sensor perfectly predicts health

✔ Prevents **machine-learning shortcut learning** and label leakage

---

### 6️⃣ Operating Regime Non-Stationarity

- Sensor distributions **shift across operating regimes**
- Peak operation increases **mean levels and variance**
- Idle operation compresses sensor ranges

✔ Enables **regime-aware ML research** under non-stationary conditions

---

### 7️⃣ Maintenance Event Validation

- Maintenance events are **sparse (~0.4%)**
- Events cluster near **critical health states**
- No deterministic or hard thresholds trigger maintenance

✔ Reflects realistic operational ambiguity and human intervention delays

---

✔ **Conclusion:**  
The dataset demonstrates realistic degradation physics, sensor behavior, and operational complexity, making it suitable for **benchmarking, research, and production-grade predictive maintenance modeling**.
