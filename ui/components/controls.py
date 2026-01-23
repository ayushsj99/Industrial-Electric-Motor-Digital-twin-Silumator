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
    
    # Generation Mode Selector
    generation_mode = st.sidebar.radio(
        "Generation Mode",
        options=["live", "instantaneous"],
        format_func=lambda x: "🔴 Live Mode" if x == "live" else "⚡ Instantaneous Mode",
        help="Live: Step-by-step generation | Instantaneous: Generate until all motors reach critical",
        horizontal=False
    )
    
    if generation_mode == "instantaneous":
        st.sidebar.info("⚡ Instant mode: Generates data until all motors reach critical state")
    else:
        st.sidebar.info("🔴 Live mode: Step-by-step data generation with real-time updates")
    
    st.sidebar.markdown("---")
    
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
        value=1.0,
        step=0.1,
        help="Multiplier for how fast motors degrade (only affects live mode, 1.0 = normal)"
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
        maintenance_cycle_period=500,
        generation_mode=generation_mode
    )
    
    return config


def render_simulation_controls(manager: SimulatorManager):
    """
    Render simulation control buttons
    """
    from simulator_manager import SimulatorState
    
    st.sidebar.subheader("Simulation Controls")
    
    # Check if instantaneous mode
    is_instantaneous = manager.config.generation_mode == "instantaneous"
    
    if is_instantaneous:
        # Instantaneous mode: Single button to generate all data
        st.sidebar.info("⚡ **Instantaneous Mode Active**")
        
        # Maintenance cycles control
        target_cycles = st.sidebar.number_input(
            "🔄 Maintenance Cycles per Motor",
            min_value=1,
            max_value=10,
            value=manager.config.target_maintenance_cycles,
            step=1,
            help="Number of complete maintenance cycles to generate for each motor. Each cycle includes degradation from healthy to critical and automatic maintenance reset."
        )
        
        # Update config if changed
        if target_cycles != manager.config.target_maintenance_cycles:
            manager.config.target_maintenance_cycles = target_cycles
        
        st.sidebar.markdown(f"Generate data for **{target_cycles} cycle(s)** per motor:")
        
        if st.sidebar.button(
            "⚡ Generate Data",
            use_container_width=True,
            type="primary",
            help=f"Generate data until all motors complete {target_cycles} maintenance cycle(s)"
        ):
            with st.spinner(f"Generating data for {target_cycles} cycle(s)... This may take a moment..."):
                manager.generate_until_all_critical()
            st.success(f"✓ Data generation complete! All motors completed {target_cycles} cycle(s).")
            st.rerun()
        
        st.sidebar.markdown("---")
        st.sidebar.caption(f"💡 Each motor will go through {target_cycles} complete degradation cycle(s), with automatic maintenance reset after reaching critical state.")
    
    else:
        # Live mode: Normal play/pause controls
        st.sidebar.info("🔴 **Live Mode Active**")
        
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
    
    # Additional step controls (available in both modes for manual stepping)
    st.sidebar.markdown("---")
    st.sidebar.markdown("**Quick Step Controls:**")
    
    col3, col4 = st.sidebar.columns(2)
    
    with col3:
        if st.button("⏭️ +50", use_container_width=True, help="Advance by 50 timesteps"):
            manager.step(num_steps=50)
            st.rerun()
    
    with col4:
        if st.button("⏭️⏭️ +100", use_container_width=True, help="Advance by 100 timesteps"):
            manager.step(num_steps=100)
            st.rerun()
    
    # Auto-run mode (only for live mode)
    st.sidebar.markdown("---")
    
    from simulator_manager import SimulatorState
    
    is_auto_running = False
    step_interval = 50
    refresh_rate = 5.0
    
    if not is_instantaneous:
        st.sidebar.markdown("**Auto-Run Settings:**")
        
        step_interval = st.sidebar.slider(
            "Steps per update",
            min_value=1,
            max_value=200,
            value=50,
            help="How many timesteps to generate per update (higher = faster data generation)"
        )
        
        refresh_rate = st.sidebar.slider(
            "Refresh rate (seconds)",
            min_value=0.1,
            max_value=10.0,
            value=5.0,
            step=0.5,
            help="How often to update the display"
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
        
        # Get CSV data and filename
        csv_data = manager.export_data()
        filename = manager.get_export_filename()
        
        # Download button
        st.sidebar.download_button(
            label="💾 Download CSV",
            data=csv_data,
            file_name=filename,
            mime="text/csv",
            use_container_width=True,
            help="Download simulation data to your computer"
        )
        
        # Show file info
        st.sidebar.caption(f"📁 Will download as: {filename}")
    else:
        st.sidebar.info("No data to export yet")


# Import pandas for timestamp
import pandas as pd


def render_motor_decision_panel(manager: SimulatorManager):
    """
    Render panel for user to decide on motor failure vs maintenance
    """
    pending = manager.get_pending_decisions()
    failed = manager.get_failed_motors()
    
    if not pending and not failed:
        return
    
    st.markdown("---")
    st.subheader("⚠️ Motor Decision Panel")
    
    # Pending Decisions
    if pending:
        st.warning(f"🚨 {len(pending)} motor(s) require your decision!")
        
        for decision in pending:
            motor_id = decision["motor_id"]
            health = decision["health"]
            hours_paused = decision["hours_paused"]
            
            with st.expander(f"⚠️ Motor {motor_id} - Health: {health:.2%} - Paused for {hours_paused:.1f} hours", expanded=True):
                st.error(f"Motor {motor_id} has reached critical health ({health:.2%})")
                st.info("**Choose an action:**")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button(f"💥 Mark as Failed", key=f"fail_{motor_id}", use_container_width=True):
                        manager.handle_motor_failure(motor_id)
                        st.success(f"Motor {motor_id} marked as failed. Data generation stopped.")
                        st.rerun()
                    st.caption("Stops data generation. Can restore later.")
                
                with col2:
                    if st.button(f"🔧 Perform Maintenance", key=f"maintain_{motor_id}", use_container_width=True):
                        manager.handle_motor_maintenance(motor_id)
                        st.success(f"Motor {motor_id} maintained. Health restored!")
                        st.rerun()
                    st.caption("Restores health and resumes operation.")
    
    # Failed Motors
    if failed:
        st.markdown("---")
        st.subheader("💀 Failed Motors")
        st.info(f"{len(failed)} motor(s) have failed and are offline")
        
        for motor_info in failed:
            motor_id = motor_info["motor_id"]
            hours_since_failure = motor_info["hours_since_failure"]
            health_at_failure = motor_info["health_at_failure"]
            
            with st.expander(f"💀 Motor {motor_id} - Failed {hours_since_failure:.1f} hours ago"):
                st.write(f"**Health at failure:** {health_at_failure:.2%}")
                st.write(f"**Offline duration:** {hours_since_failure:.1f} hours")
                
                if st.button(f"🔄 Restore Motor {motor_id}", key=f"restore_{motor_id}", use_container_width=True):
                    manager.restore_failed_motor(motor_id)
                    st.success(f"Motor {motor_id} restored with good health and synced to current time!")
                    st.rerun()
                st.caption("Restores motor to full health, synced with current simulation time.")
