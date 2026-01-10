"""
Chart Components - Reusable Plotly visualization components
"""
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import List


def plot_time_series(df: pd.DataFrame, columns: List[str], title: str = "Time Series"):
    """
    Create multi-line time series plot
    """
    if df.empty:
        st.info("No data available yet")
        return
    
    fig = go.Figure()
    
    # Check if multi-motor data
    has_motors = "motor_id" in df.columns
    
    if has_motors:
        motor_ids = df["motor_id"].unique()
        
        for motor_id in motor_ids:
            motor_df = df[df["motor_id"] == motor_id]
            
            for col in columns:
                fig.add_trace(go.Scatter(
                    x=motor_df["time"],
                    y=motor_df[col],
                    mode='lines',
                    name=f"Motor {motor_id} - {col}",
                    line=dict(width=1.5),
                    opacity=0.7
                ))
    else:
        for col in columns:
            fig.add_trace(go.Scatter(
                x=df["time"],
                y=df[col],
                mode='lines',
                name=col,
                line=dict(width=2)
            ))
    
    fig.update_layout(
        title=title,
        xaxis_title="Time Step",
        yaxis_title="Value",
        hovermode='x unified',
        height=400,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_sensor_grid(df: pd.DataFrame):
    """
    Create 2x2 grid of sensor plots
    """
    if df.empty:
        st.info("No data available yet")
        return
    
    # Create subplots
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("Temperature", "Vibration", "Current", "RPM"),
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )
    
    sensors = [
        ("temperature", 1, 1),
        ("vibration", 1, 2),
        ("current", 2, 1),
        ("rpm", 2, 2)
    ]
    
    has_motors = "motor_id" in df.columns
    
    if has_motors:
        motor_ids = df["motor_id"].unique()
        colors = px.colors.qualitative.Plotly
        
        for idx, motor_id in enumerate(motor_ids):
            motor_df = df[df["motor_id"] == motor_id]
            color = colors[idx % len(colors)]
            
            for sensor, row, col in sensors:
                showlegend = (row == 1 and col == 1)  # Only show legend once
                
                fig.add_trace(
                    go.Scatter(
                        x=motor_df["time"],
                        y=motor_df[sensor],
                        mode='lines',
                        name=f"Motor {motor_id}",
                        line=dict(color=color, width=1.5),
                        showlegend=showlegend,
                        legendgroup=f"motor_{motor_id}"
                    ),
                    row=row, col=col
                )
    else:
        for sensor, row, col in sensors:
            fig.add_trace(
                go.Scatter(
                    x=df["time"],
                    y=df[sensor],
                    mode='lines',
                    line=dict(width=2),
                    showlegend=False
                ),
                row=row, col=col
            )
    
    fig.update_layout(
        height=600,
        showlegend=has_motors,
        hovermode='x unified'
    )
    
    fig.update_xaxes(title_text="Time", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=2)
    
    st.plotly_chart(fig, use_container_width=True)


def plot_health_bars(status_df: pd.DataFrame):
    """
    Create horizontal bar chart showing health of all motors
    """
    if status_df.empty:
        st.info("No motor status data available")
        return
    
    # Sort by health
    status_df = status_df.sort_values("motor_health")
    
    # Color bars based on health
    colors = []
    for health in status_df["motor_health"]:
        if health > 0.7:
            colors.append("#2ecc71")  # Green - healthy
        elif health > 0.4:
            colors.append("#f39c12")  # Orange - warning
        else:
            colors.append("#e74c3c")  # Red - critical
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        y=[f"Motor {mid}" for mid in status_df["motor_id"]],
        x=status_df["motor_health"],
        orientation='h',
        marker=dict(color=colors),
        text=[f"{h:.2%}" for h in status_df["motor_health"]],
        textposition='auto',
        hovertemplate=(
            "<b>Motor %{y}</b><br>" +
            "Health: %{x:.2%}<br>" +
            "<extra></extra>"
        )
    ))
    
    fig.update_layout(
        title="Motor Health Status",
        xaxis_title="Motor Health",
        yaxis_title="Motor ID",
        height=max(300, len(status_df) * 40),
        xaxis=dict(range=[0, 1]),
        showlegend=False
    )
    
    # Add threshold line
    fig.add_vline(
        x=0.3,
        line_dash="dash",
        line_color="red",
        annotation_text="Alert Threshold",
        annotation_position="top"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_health_vs_sensor(df: pd.DataFrame, sensor: str = "vibration"):
    """
    Create scatter plot of health vs sensor reading
    """
    if df.empty:
        st.info("No data available yet")
        return
    
    fig = go.Figure()
    
    has_motors = "motor_id" in df.columns
    
    if has_motors:
        motor_ids = df["motor_id"].unique()
        colors = px.colors.qualitative.Plotly
        
        for idx, motor_id in enumerate(motor_ids):
            motor_df = df[df["motor_id"] == motor_id]
            
            fig.add_trace(go.Scatter(
                x=motor_df["motor_health"],
                y=motor_df[sensor],
                mode='markers',
                name=f"Motor {motor_id}",
                marker=dict(
                    size=4,
                    color=colors[idx % len(colors)],
                    opacity=0.6
                )
            ))
    else:
        fig.add_trace(go.Scatter(
            x=df["motor_health"],
            y=df[sensor],
            mode='markers',
            marker=dict(size=4, opacity=0.6)
        ))
    
    fig.update_layout(
        title=f"Motor Health vs {sensor.title()}",
        xaxis_title="Motor Health",
        yaxis_title=sensor.title(),
        height=400,
        hovermode='closest'
    )
    
    # Invert x-axis (healthy to failed)
    fig.update_xaxes(autorange="reversed")
    
    st.plotly_chart(fig, use_container_width=True)


def plot_correlation_heatmap(df: pd.DataFrame):
    """
    Create correlation matrix heatmap
    """
    if df.empty:
        st.info("No data available yet")
        return
    
    # Select numeric columns
    numeric_cols = ["temperature", "vibration", "current", "rpm", "motor_health"]
    
    # Filter columns that exist
    available_cols = [col for col in numeric_cols if col in df.columns]
    
    if len(available_cols) < 2:
        st.warning("Not enough data for correlation analysis")
        return
    
    # Calculate correlation
    corr = df[available_cols].corr()
    
    fig = go.Figure(data=go.Heatmap(
        z=corr.values,
        x=corr.columns,
        y=corr.columns,
        colorscale='RdBu',
        zmid=0,
        text=corr.values,
        texttemplate='%{text:.2f}',
        textfont={"size": 10},
        colorbar=dict(title="Correlation")
    ))
    
    fig.update_layout(
        title="Sensor Correlation Matrix",
        height=400,
        xaxis=dict(side='bottom')
    )
    
    st.plotly_chart(fig, use_container_width=True)


def plot_realtime_dashboard(df: pd.DataFrame, window: int = 50):
    """
    Create a compact real-time dashboard view
    """
    if df.empty:
        st.info("No data available yet")
        return
    
    # Get recent data
    max_time = df["time"].max()
    recent_df = df[df["time"] >= max_time - window]
    
    # Create 2-row dashboard
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=("Motor Health", "Sensor Readings"),
        row_heights=[0.4, 0.6],
        vertical_spacing=0.15
    )
    
    has_motors = "motor_id" in recent_df.columns
    
    if has_motors:
        motor_ids = recent_df["motor_id"].unique()
        colors = px.colors.qualitative.Plotly
        
        # Health traces
        for idx, motor_id in enumerate(motor_ids):
            motor_df = recent_df[recent_df["motor_id"] == motor_id]
            color = colors[idx % len(colors)]
            
            # Health line
            fig.add_trace(
                go.Scatter(
                    x=motor_df["time"],
                    y=motor_df["motor_health"],
                    mode='lines+markers',
                    name=f"Motor {motor_id}",
                    line=dict(color=color, width=2),
                    marker=dict(size=4),
                    legendgroup=f"motor_{motor_id}"
                ),
                row=1, col=1
            )
            
            # Vibration line
            fig.add_trace(
                go.Scatter(
                    x=motor_df["time"],
                    y=motor_df["vibration"],
                    mode='lines',
                    name=f"Motor {motor_id} - Vib",
                    line=dict(color=color, width=1.5, dash='dot'),
                    showlegend=False,
                    legendgroup=f"motor_{motor_id}"
                ),
                row=2, col=1
            )
    
    fig.update_layout(
        height=500,
        showlegend=True,
        hovermode='x unified'
    )
    
    fig.update_yaxes(title_text="Health", row=1, col=1)
    fig.update_yaxes(title_text="Vibration", row=2, col=1)
    fig.update_xaxes(title_text="Time", row=2, col=1)
    
    st.plotly_chart(fig, use_container_width=True)
