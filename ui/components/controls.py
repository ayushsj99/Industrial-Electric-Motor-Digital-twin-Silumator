"""
Control Panel Components - Interactive widgets for simulator control
"""
import streamlit as st
from simulator_manager import SimulatorConfig, SimulatorManager


def render_control_panel(manager: SimulatorManager) -> SimulatorConfig:
    """
    Render the control panel with all configuration options
    Returns the current configuration
    """
    st.sidebar.header("🎛️ Control Panel")
    
    # Simulator Configuration Section
    st.sidebar.subheader("Simulator Configuration")
    
    num_motors = st.sidebar.slider(
        "Number of Motors",
        min_value=1,
        max_value=20,
        value=manager.config.num_motors,
        step=1,
        help="Total number of motors in the factory"
    )
    
    degradation_speed = st.sidebar.slider(
        "Degradation Speed",
        min_value=0.1,
        max_value=5.0,
        value=manager.config.degradation_speed,
        step=0.1,
        help="Multiplier for how fast motors degrade (1.0 = normal)"
    )
    
    noise_level = st.sidebar.slider(
        "Sensor Noise Level",
        min_value=0.0,
        max_value=3.0,
        value=manager.config.noise_level,
        step=0.1,
        help="Multiplier for sensor noise (0 = perfect, 1.0 = realistic)"
    )
    
    load_factor = st.sidebar.slider(
        "Load Factor",
        min_value=0.5,
        max_value=2.0,
        value=manager.config.load_factor,
        step=0.1,
        help="Operating load multiplier (higher = more stress)"
    )
    
    # Alert Settings
    st.sidebar.subheader("Alert Settings")
    
    alert_threshold = st.sidebar.slider(
        "Health Alert Threshold",
        min_value=0.1,
        max_value=0.9,
        value=manager.alert_threshold,
        step=0.05,
        help="Trigger alert when health drops below this value"
    )
    manager.alert_threshold = alert_threshold
    
    # Create new config
    config = SimulatorConfig(
        num_motors=num_motors,
        degradation_speed=degradation_speed,
        noise_level=noise_level,
        load_factor=load_factor,
        auto_maintenance_enabled=True,
        maintenance_cycle_period=500
    )
    
    return config


def render_simulation_controls(manager: SimulatorManager):
    """
    Render simulation control buttons
    """
    from simulator_manager import SimulatorState
    
    st.sidebar.subheader("Simulation Controls")
    
    # Primary controls: Play/Pause/Stop
    col1, col2, col3 = st.sidebar.columns(3)
    
    with col1:
        if manager.state == SimulatorState.RUNNING:
            if st.button("⏸️ Pause", use_container_width=True, help="Pause simulation"):
                manager.pause()
                st.rerun()
        else:
            if st.button("▶️ Play", use_container_width=True, help="Start/Resume simulation"):
                manager.resume()
                st.rerun()
    
    with col2:
        if st.button("⏹️ Stop", use_container_width=True, help="Stop simulation"):
            manager.stop()
            st.rerun()
    
    with col3:
        if st.button("🔄 Restart", use_container_width=True, help="Restart from beginning"):
            manager.restart()
            st.rerun()
    
    st.sidebar.markdown("**Manual Step Controls:**")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("➡️ +1", use_container_width=True, help="Advance by 1 timestep"):
            manager.step(num_steps=1)
            st.rerun()
    
    with col2:
        if st.button("⏩ +10", use_container_width=True, help="Advance by 10 timesteps"):
            manager.step(num_steps=10)
            st.rerun()
    
    col3, col4 = st.sidebar.columns(2)
    
    with col3:
        if st.button("⏭️ +50", use_container_width=True, help="Advance by 50 timesteps"):
            manager.step(num_steps=50)
            st.rerun()
    
    with col4:
        if st.button("⏭️⏭️ +100", use_container_width=True, help="Advance by 100 timesteps"):
            manager.step(num_steps=100)
            st.rerun()
    
    # Auto-run mode
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Auto-Run Settings:**")
    
    from simulator_manager import SimulatorState
    
    step_interval = st.sidebar.slider(
        "Steps per update",
        min_value=1,
        max_value=50,
        value=5,
        help="How many steps to take each update"
    )
    
    refresh_rate = st.sidebar.slider(
        "Refresh rate (seconds)",
        min_value=0.1,
        max_value=5.0,
        value=1.0,
        step=0.1,
        help="How often to update"
    )
    
    # Return whether auto-run is active
    is_auto_running = manager.state == SimulatorState.RUNNING
    
    return is_auto_running, step_interval, refresh_rate


def render_motor_actions(manager: SimulatorManager):
    """
    Render motor-specific action controls
    """
    st.sidebar.subheader("Motor Actions")
    
    if manager.factory is None:
        st.sidebar.info("Initialize simulator first")
        return
    
    motor_ids = [motor.motor_id for motor in manager.factory.motors]
    
    selected_motor = st.sidebar.selectbox(
        "Select Motor",
        options=motor_ids,
        help="Choose a motor to perform actions on"
    )
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("💥 Inject Failure", use_container_width=True):
            manager.inject_failure(selected_motor)
            st.success(f"Failure injected to Motor {selected_motor}")
            st.rerun()
    
    with col2:
        if st.button("🔧 Maintenance", use_container_width=True):
            manager.reset_motor(selected_motor)
            st.success(f"Motor {selected_motor} maintained")
            st.rerun()


def render_export_controls(manager: SimulatorManager):
    """
    Render data export controls
    """
    st.sidebar.subheader("Data Export")
    
    if manager.history:
        total_records = len(manager.history)
        st.sidebar.info(f"📊 {total_records} records in history")
        
        if st.sidebar.button("💾 Export to CSV", use_container_width=True):
            timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
            filepath = f"data/simulated/export_{timestamp}.csv"
            
            # Ensure directory exists
            import os
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            manager.export_data(filepath)
            st.sidebar.success(f"Exported to {filepath}")
    else:
        st.sidebar.info("No data to export yet")


# Import pandas for timestamp
import pandas as pd
