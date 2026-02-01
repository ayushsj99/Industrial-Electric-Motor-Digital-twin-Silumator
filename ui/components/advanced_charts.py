"""
Advanced Chart Components - Phase 6 Improvements Visualization

Specialized charts for:
- Stochastic degradation burst patterns
- Asynchronous sensor response lag
- Operating regime transitions
- Sensor imperfections
- Maintenance events
"""
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import List


def plot_health_with_bursts(df: pd.DataFrame):
    """
    Visualize stochastic degradation with burst events highlighted.
    Shows the jagged, non-linear health decay.
    """
    if df.empty or "motor_health" not in df.columns:
        st.info("No health data available")
        return
    
    fig = go.Figure()
    
    has_motors = "motor_id" in df.columns
    
    if has_motors:
        motor_ids = df["motor_id"].unique()
        
        for motor_id in motor_ids[:5]:  # Limit to 5 for clarity
            motor_df = df[df["motor_id"] == motor_id].copy()
            
            # Calculate step-to-step health drops to identify bursts
            motor_df["health_drop"] = -motor_df["motor_health"].diff()
            
            # Identify burst events (drops > 0.01)
            bursts = motor_df[motor_df["health_drop"] > 0.01]
            
            # Plot health line
            fig.add_trace(go.Scatter(
                x=motor_df["time"],
                y=motor_df["motor_health"],
                mode='lines',
                name=f"Motor {motor_id}",
                line=dict(width=2),
                opacity=0.8
            ))
            
            # Highlight burst events
            if not bursts.empty:
                fig.add_trace(go.Scatter(
                    x=bursts["time"],
                    y=bursts["motor_health"],
                    mode='markers',
                    name=f"Motor {motor_id} Bursts",
                    marker=dict(
                        size=10,
                        symbol='x',
                        color='red'
                    ),
                    showlegend=False
                ))
    
    fig.update_layout(
        title="Stochastic Health Degradation (Burst Events Highlighted)",
        xaxis_title="Time Step",
        yaxis_title="Motor Health",
        height=400,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig, width='stretch')


def plot_sensor_response_lag(df: pd.DataFrame):
    """
    Visualize asynchronous sensor response.
    Shows vibration (immediate), current (short lag), temperature (long lag).
    """
    if df.empty:
        st.info("No data available")
        return
    
    # Focus on one motor for clarity
    if "motor_id" in df.columns:
        motor_df = df[df["motor_id"] == df["motor_id"].iloc[0]].copy()
    else:
        motor_df = df.copy()
    
    # Normalize sensors to [0, 1] for comparison
    for col in ["vibration", "current", "temperature"]:
        if col in motor_df.columns:
            min_val = motor_df[col].min()
            max_val = motor_df[col].max()
            if max_val > min_val:
                motor_df[f"{col}_norm"] = (motor_df[col] - min_val) / (max_val - min_val)
    
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Health Degradation", "Normalized Sensor Responses"),
        vertical_spacing=0.15,
        row_heights=[0.3, 0.7]
    )
    
    # Top: Health
    fig.add_trace(
        go.Scatter(
            x=motor_df["time"],
            y=motor_df["motor_health"],
            mode='lines',
            name="Health",
            line=dict(color='black', width=3)
        ),
        row=1, col=1
    )
    
    # Bottom: Sensors
    colors = {"vibration": "red", "current": "orange", "temperature": "blue"}
    for sensor in ["vibration", "current", "temperature"]:
        norm_col = f"{sensor}_norm"
        if norm_col in motor_df.columns:
            fig.add_trace(
                go.Scatter(
                    x=motor_df["time"],
                    y=motor_df[norm_col],
                    mode='lines',
                    name=f"{sensor.title()} (lag)",
                    line=dict(color=colors[sensor], width=2)
                ),
                row=2, col=1
            )
    
    fig.update_layout(
        height=600,
        showlegend=True,
        hovermode='x unified',
        title="Asynchronous Sensor Response Analysis"
    )
    
    fig.update_yaxes(title_text="Health", row=1, col=1)
    fig.update_yaxes(title_text="Normalized Value", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    
    st.plotly_chart(fig, width='stretch')


def plot_operating_regimes(df: pd.DataFrame):
    """
    Visualize operating regime transitions over time.
    """
    if df.empty or "regime" not in df.columns:
        st.info("No regime data available")
        return
    
    # Get first motor's data
    if "motor_id" in df.columns:
        motor_df = df[df["motor_id"] == df["motor_id"].iloc[0]].copy()
    else:
        motor_df = df.copy()
    
    # Map regimes to numeric values for coloring
    regime_map = {"idle": 0, "normal": 1, "peak": 2}
    motor_df["regime_num"] = motor_df["regime"].map(regime_map)
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=("Operating Regime", "Current Draw", "Temperature"),
        vertical_spacing=0.12,
        row_heights=[0.2, 0.4, 0.4]
    )
    
    # Top: Regime indicator
    fig.add_trace(
        go.Scatter(
            x=motor_df["time"],
            y=motor_df["regime_num"],
            mode='lines',
            name="Regime",
            line=dict(width=3, shape='hv'),
            fill='tozeroy',
            fillcolor='rgba(0,100,200,0.2)'
        ),
        row=1, col=1
    )
    
    # Middle: Current (responds to load)
    fig.add_trace(
        go.Scatter(
            x=motor_df["time"],
            y=motor_df["current"],
            mode='lines',
            name="Current",
            line=dict(color='orange', width=2)
        ),
        row=2, col=1
    )
    
    # Bottom: Temperature
    fig.add_trace(
        go.Scatter(
            x=motor_df["time"],
            y=motor_df["temperature"],
            mode='lines',
            name="Temperature",
            line=dict(color='red', width=2)
        ),
        row=3, col=1
    )
    
    fig.update_layout(
        height=700,
        showlegend=False,
        hovermode='x unified',
        title="Operating Regime Transitions"
    )
    
    fig.update_yaxes(title_text="Regime", row=1, col=1, tickvals=[0, 1, 2], ticktext=["Idle", "Normal", "Peak"])
    fig.update_yaxes(title_text="Current (A)", row=2, col=1)
    fig.update_yaxes(title_text="Temp (°C)", row=3, col=1)
    fig.update_xaxes(title_text="Time", row=3, col=1)
    
    st.plotly_chart(fig, width='stretch')


def plot_maintenance_events(df: pd.DataFrame):
    """
    Visualize maintenance events and their impact on health.
    """
    if df.empty or "maintenance_event" not in df.columns:
        st.info("No maintenance data available")
        return
    
    fig = go.Figure()
    
    has_motors = "motor_id" in df.columns
    
    if has_motors:
        motor_ids = df["motor_id"].unique()
        
        for motor_id in motor_ids[:5]:
            motor_df = df[df["motor_id"] == motor_id].copy()
            
            # Plot health
            fig.add_trace(go.Scatter(
                x=motor_df["time"],
                y=motor_df["motor_health"],
                mode='lines',
                name=f"Motor {motor_id}",
                line=dict(width=2)
            ))
            
            # Highlight maintenance events
            maintenance_df = motor_df[motor_df["maintenance_event"].notna()]
            
            if not maintenance_df.empty:
                fig.add_trace(go.Scatter(
                    x=maintenance_df["time"],
                    y=maintenance_df["motor_health"],
                    mode='markers',
                    name=f"Motor {motor_id} Maintenance",
                    marker=dict(
                        size=15,
                        symbol='star',
                        color='green',
                        line=dict(color='darkgreen', width=2)
                    ),
                    showlegend=True
                ))
    
    fig.update_layout(
        title="Maintenance Events and Health Recovery",
        xaxis_title="Time Step",
        yaxis_title="Motor Health",
        height=500,
        hovermode='x unified',
        annotations=[
            dict(
                text="⭐ = Maintenance Event",
                xref="paper", yref="paper",
                x=0.02, y=0.98,
                showarrow=False,
                bgcolor="rgba(255,255,255,0.8)"
            )
        ]
    )
    
    st.plotly_chart(fig, width='stretch')


def plot_sensor_quality_indicators(df: pd.DataFrame):
    """
    Show sensor quality degradation over time (flatlines, intermittent failures).
    """
    if df.empty:
        st.info("No data available")
        return
    
    # Focus on one motor
    if "motor_id" in df.columns:
        motor_df = df[df["motor_id"] == df["motor_id"].iloc[0]].copy()
    else:
        motor_df = df.copy()
    
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Temperature", "Vibration", "Current", "RPM"),
        vertical_spacing=0.15
    )
    
    sensors = [
        ("temperature", 1, 1),
        ("vibration", 1, 2),
        ("current", 2, 1),
        ("rpm", 2, 2)
    ]
    
    for sensor, row, col in sensors:
        if sensor in motor_df.columns:
            # Plot sensor data
            fig.add_trace(
                go.Scatter(
                    x=motor_df["time"],
                    y=motor_df[sensor],
                    mode='lines+markers',
                    name=sensor.title(),
                    marker=dict(size=3),
                    line=dict(width=1),
                    showlegend=False
                ),
                row=row, col=col
            )
            
            # Highlight missing values
            missing = motor_df[motor_df[sensor].isna()]
            if not missing.empty:
                fig.add_trace(
                    go.Scatter(
                        x=missing["time"],
                        y=[motor_df[sensor].mean()] * len(missing),
                        mode='markers',
                        marker=dict(size=8, symbol='x', color='red'),
                        name=f"{sensor} missing",
                        showlegend=False
                    ),
                    row=row, col=col
                )
    
    fig.update_layout(
        height=600,
        title="Sensor Imperfections (Missing Data Highlighted)",
        hovermode='closest'
    )
    
    st.plotly_chart(fig, width='stretch')
