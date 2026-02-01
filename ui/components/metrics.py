"""
Metrics Components - KPI displays and status indicators
"""
import streamlit as st
import pandas as pd
from typing import List, Dict


def render_kpi_metrics(manager):
    """
    Render top-level KPI metrics with categorical health states
    """
    status_df = manager.get_motor_status()
    
    if status_df.empty:
        st.info("Initialize simulator to see metrics")
        return
    
    # Calculate metrics based on categorical states
    total_motors = len(status_df)
    healthy_motors = len(status_df[status_df["health_state"] == "Healthy"])
    warning_motors = len(status_df[status_df["health_state"] == "Warning"])
    critical_motors = len(status_df[status_df["health_state"] == "Critical"])
    avg_health = status_df["motor_health"].mean()
    
    # Calculate average operating hours
    avg_hours = status_df.get("hours_since_maintenance", pd.Series([0])).mean()
    
    # Display metrics in columns
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    with col1:
        st.metric(
            label="⚙️ Total Motors",
            value=total_motors,
            delta=None
        )
    
    with col2:
        st.metric(
            label="✅ Healthy",
            value=healthy_motors,
            delta=None,
            help="Health State: Healthy"
        )
    
    with col3:
        st.metric(
            label="⚠️ Warning",
            value=warning_motors,
            delta=None,
            help="Health State: Warning"
        )
    
    with col4:
        st.metric(
            label="🚨 Critical",
            value=critical_motors,
            delta=None,
            help="Health State: Critical"
        )
    
    with col5:
        st.metric(
            label="📊 Avg Health",
            value=f"{avg_health:.1%}",
            delta=None
        )
    
    with col6:
        st.metric(
            label="⏱️ Avg Hours",
            value=f"{avg_hours:.0f}h",
            delta=None,
            help="Average operating hours since last maintenance"
        )


def render_alert_panel(alerts: List[Dict]):
    """
    Render alert notifications with categorical health states
    """
    if not alerts:
        st.success("✅ All systems nominal")
        return
    
    st.warning(f"🚨 {len(alerts)} Active Alert(s)")
    
    for alert in alerts:
        state = alert.get('health_state', 'Unknown')
        icon = "🚨" if state == "Critical" else "⚠️"
        
        with st.expander(f"{icon} Motor {alert['motor_id']} - {state}", expanded=True):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Health State", state)
            
            with col2:
                st.metric("Health Score", f"{alert['health']:.1%}")
            
            with col3:
                st.metric("Operating Hours", f"{alert.get('hours_since_maintenance', 0):.0f}h")
            
            with col4:
                st.metric("Vibration", f"{alert['vibration']:.2f}")
            
            if state == "Critical":
                st.error("🚨 Motor in critical condition")
            else:
                st.warning("⚠️ Monitor closely - maintenance may be needed soon")


def render_motor_table(status_df: pd.DataFrame):
    """
    Render detailed motor status table with categorical health
    """
    if status_df.empty:
        st.info("No motor data available")
        return
    
    # Prepare display dataframe - include health_state and operating hours
    columns_to_show = [
        "motor_id",
        "health_state",
        "motor_health",
        "hours_since_maintenance",
        "temperature",
        "vibration",
        "current",
        "rpm"
    ]
    
    # Only include columns that exist
    available_columns = [col for col in columns_to_show if col in status_df.columns]
    display_df = status_df[available_columns].copy()
    
    # Format columns
    if "motor_health" in display_df.columns:
        display_df["motor_health"] = display_df["motor_health"].apply(lambda x: f"{x:.1%}")
    if "hours_since_maintenance" in display_df.columns:
        display_df["hours_since_maintenance"] = display_df["hours_since_maintenance"].apply(lambda x: f"{x:.0f}h")
    if "temperature" in display_df.columns:
        display_df["temperature"] = display_df["temperature"].apply(lambda x: f"{x:.1f}°C")
    if "vibration" in display_df.columns:
        display_df["vibration"] = display_df["vibration"].apply(lambda x: f"{x:.3f}")
    if "current" in display_df.columns:
        display_df["current"] = display_df["current"].apply(lambda x: f"{x:.2f}A")
    if "rpm" in display_df.columns:
        display_df["rpm"] = display_df["rpm"].apply(lambda x: f"{x:.0f}")
    
    # Rename columns for display
    column_names = {
        "motor_id": "Motor ID",
        "health_state": "State",
        "motor_health": "Health %",
        "hours_since_maintenance": "Op Hours",
        "temperature": "Temp",
        "vibration": "Vibration",
        "current": "Current",
        "rpm": "RPM"
    }
    display_df.rename(columns={k: v for k, v in column_names.items() if k in display_df.columns}, inplace=True)
    
    # Add status indicator
    def get_status(health_str):
        health = float(health_str.strip('%')) / 100
        if health > 0.7:
            return "✅"
        elif health > 0.4:
            return "⚠️"
        else:
            return "🚨"
    
    display_df.insert(0, "Status", display_df["Health"].apply(get_status))
    
    st.dataframe(
        display_df,
        width='stretch',
        hide_index=True
    )


def render_simulation_info(manager):
    """
    Render simulation metadata and info
    """
    st.subheader("Simulation Info")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Timestep", manager.current_time)
    
    with col2:
        st.metric("History Records", len(manager.history))
    
    with col3:
        from simulator_manager import SimulatorState
        
        status_map = {
            SimulatorState.RUNNING: "▶️ Running",
            SimulatorState.PAUSED: "⏸️ Paused",
            SimulatorState.STOPPED: "⏹️ Stopped"
        }
        st.metric("Status", status_map.get(manager.state, "Unknown"))
    
    # Configuration details
    with st.expander("Configuration Details"):
        st.write("**Simulator Parameters:**")
        st.write(f"- Motors: {manager.config.num_motors}")
        st.write(f"- Degradation Speed: {manager.config.degradation_speed}x")
        st.write(f"- Noise Level: {manager.config.noise_level}x")
        st.write(f"- Load Factor: {manager.config.load_factor}x")
        st.write(f"- Alert Threshold: {manager.alert_threshold:.0%}")


def render_fleet_overview(status_df: pd.DataFrame):
    """
    Render fleet-level statistics
    """
    if status_df.empty:
        return
    
    st.subheader("Fleet Statistics")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Health Distribution:**")
        health_stats = status_df["motor_health"].describe()
        st.write(f"- Min: {health_stats['min']:.1%}")
        st.write(f"- Mean: {health_stats['mean']:.1%}")
        st.write(f"- Max: {health_stats['max']:.1%}")
        st.write(f"- Std: {health_stats['std']:.3f}")
    
    with col2:
        st.write("**Sensor Averages:**")
        st.write(f"- Avg Temperature: {status_df['temperature'].mean():.1f}°C")
        st.write(f"- Avg Vibration: {status_df['vibration'].mean():.3f}")
        st.write(f"- Avg Current: {status_df['current'].mean():.2f}A")
        st.write(f"- Avg RPM: {status_df['rpm'].mean():.0f}")


def render_status_badge(health: float) -> str:
    """
    Return HTML badge for health status
    """
    if health > 0.7:
        color = "green"
        label = "HEALTHY"
    elif health > 0.4:
        color = "orange"
        label = "WARNING"
    else:
        color = "red"
        label = "CRITICAL"
    
    return f'<span style="background-color:{color};color:white;padding:4px 8px;border-radius:4px;font-weight:bold;">{label}</span>'
