"""
Industrial Predictive Maintenance Simulator - Streamlit Control Panel
Main application entry point
"""
import streamlit as st
import sys
import os
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from ui.simulator_manager import SimulatorManager, SimulatorConfig
except ImportError:
    from simulator_manager import SimulatorManager, SimulatorConfig

try:
    from ui.components.controls import (
        render_control_panel,
        render_simulation_controls,
        render_export_controls,
        render_motor_decision_panel
    )
    from ui.components.charts import (
        plot_sensor_grid,
        plot_health_bars,
        plot_health_vs_sensor,
        plot_correlation_heatmap,
        plot_realtime_dashboard
    )
    from ui.components.advanced_charts import (
        plot_health_with_bursts,
        plot_sensor_response_lag,
        plot_operating_regimes,
        plot_maintenance_events,
        plot_sensor_quality_indicators
    )
    from ui.components.metrics import (
        render_kpi_metrics,
        render_alert_panel,
        render_motor_table,
        render_simulation_info,
        render_fleet_overview
    )
    from ui.components.verification_charts import (
        render_data_verification_view
    )
except ImportError:
    from components.controls import (
        render_control_panel,
        render_simulation_controls,
        render_export_controls,
        render_motor_decision_panel
    )
    from components.charts import (
        plot_sensor_grid,
        plot_health_bars,
        plot_health_vs_sensor,
        plot_correlation_heatmap,
        plot_realtime_dashboard
    )
    from components.advanced_charts import (
        plot_health_with_bursts,
        plot_sensor_response_lag,
        plot_operating_regimes,
        plot_maintenance_events,
        plot_sensor_quality_indicators
    )
    from components.metrics import (
        render_kpi_metrics,
        render_alert_panel,
        render_motor_table,
        render_simulation_info,
        render_fleet_overview
    )
    from components.verification_charts import (
        render_data_verification_view
    )


# Page configuration - moved to root app.py for Hugging Face deployment
# Keeping this here for standalone use but wrapped in try-except
try:
    st.set_page_config(
        page_title="Industrial Maintenance Simulator",
        page_icon="🏭",
        layout="wide",
        initial_sidebar_state="expanded"
    )
except st.errors.StreamlitAPIException:
    # Page config already set (e.g., by root app.py)
    pass


def initialize_session_state():
    """Initialize Streamlit session state"""
    if "manager" not in st.session_state:
        st.session_state.manager = SimulatorManager()
    
    if "initialized" not in st.session_state:
        st.session_state.initialized = False
    
    if "view_mode" not in st.session_state:
        st.session_state.view_mode = "Dashboard"


def main():
    """Main application"""
    initialize_session_state()
    
    manager = st.session_state.manager
    
    # Header
    st.title("🏭 Industrial Predictive Maintenance Simulator")
    st.markdown("**Real-time Digital Twin Control Panel**")
    st.markdown("---")
    
    # Sidebar Controls
    st.sidebar.title("🎮 Control Center")
    
    # Configuration controls
    config = render_control_panel(manager)
    
    # Initialize/Reinitialize button
    if not st.session_state.initialized:
        st.sidebar.markdown("---")
        if st.sidebar.button("🚀 Initialize Simulator", type="primary", use_container_width=True):
            with st.spinner("Initializing factory simulator..."):
                manager.initialize(config)
                st.session_state.initialized = True
                st.success("✅ Simulator initialized!")
                time.sleep(0.5)
                st.rerun()
    else:
        # Check if config changed
        config_changed = (
            config.num_motors != manager.config.num_motors or
            abs(config.degradation_speed - getattr(manager.config, 'degradation_speed', 1.0)) > 0.01 or
            abs(config.noise_level - manager.config.noise_level) > 0.01 or
            abs(config.load_factor - manager.config.load_factor) > 0.01 or
            config.auto_maintenance_enabled != manager.config.auto_maintenance_enabled or
            config.maintenance_cycle_period != manager.config.maintenance_cycle_period or
            config.generation_mode != manager.config.generation_mode or
            config.target_maintenance_cycles != getattr(manager.config, 'target_maintenance_cycles', 1) or
            abs(config.warning_threshold - getattr(manager.config, 'warning_threshold', 0.4)) > 0.01 or
            abs(config.critical_threshold - getattr(manager.config, 'critical_threshold', 0.2)) > 0.01
        )
        
        if config_changed:
            st.sidebar.info("🔧 Configuration updated")
            with st.spinner("Applying configuration..."):
                manager.update_configuration(config)
                st.sidebar.success("✅ Applied without losing data!")
                time.sleep(0.3)
                st.rerun()
            
            # Optional full restart button
            with st.sidebar.expander("🔄 Advanced Options"):
                st.caption("Only use if experiencing issues")
                if st.button("🔄 Full Restart", use_container_width=True):
                    with st.spinner("Performing full restart..."):
                        manager.initialize(config)
                        st.success("✅ Full restart completed!")
                        time.sleep(0.5)
                        st.rerun()
        
        st.sidebar.markdown("---")
        
        # Simulation controls
        auto_run_result = render_simulation_controls(manager)
        
        st.sidebar.markdown("---")
        
        # Export controls
        render_export_controls(manager)
    
    # Main content area
    if not st.session_state.initialized:
        st.info("👈 Configure parameters and click **Initialize Simulator** to start")
        
        # Show welcome guide
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🎯 Features")
            st.markdown("""
            - **Multi-Motor Simulation**: Monitor fleet of machines
            - **Real-time Monitoring**: Live sensor data streaming
            - **Physics-Based**: Realistic degradation models
            - **Interactive Controls**: Adjust parameters on the fly
            - **Failure Injection**: Test scenarios and responses
            - **Data Export**: Save simulation data for ML training
            """)
        
        with col2:
            st.subheader("🚀 Quick Start")
            st.markdown("""
            1. **Configure** simulation parameters in the sidebar
            2. **Initialize** the simulator
            3. **Step** through time or enable auto-run mode
            4. **Monitor** health metrics and alerts
            5. **Inject failures** to test scenarios
            6. **Export** data for analysis
            """)
        
        return
    
    # View mode selector
    view_mode = st.radio(
        "View Mode:",
        ["Dashboard", "Detailed Analysis", "Advanced Features", "Fleet Status", "Raw Data", "Data Verification"],
        horizontal=True,
        key="view_mode_selector"
    )
    
    st.markdown("---")
    
    # Motor Decision Panel (for live mode critical motors)
    if manager.config.generation_mode == "live":
        render_motor_decision_panel(manager)
    
    # Get data
    history_df = manager.get_history_df()
    status_df = manager.get_motor_status()
    alerts = manager.get_alerts()
    
    # Render based on view mode
    if view_mode == "Dashboard":
        render_dashboard_view(manager, history_df, status_df, alerts)
    
    elif view_mode == "Detailed Analysis":
        render_analysis_view(manager, history_df, status_df)
    
    elif view_mode == "Advanced Features":
        render_advanced_view(manager, history_df)
    
    elif view_mode == "Fleet Status":
        render_fleet_view(manager, status_df)
    
    elif view_mode == "Raw Data":
        render_data_view(history_df, status_df)
    
    elif view_mode == "Data Verification":
        render_data_verification_view(history_df, manager)
    
    # Auto-run logic (only if running state)
    if st.session_state.initialized and auto_run_result[0]:
        step_interval = auto_run_result[1]
        refresh_rate = auto_run_result[2]
        time.sleep(refresh_rate)
        manager.step(num_steps=step_interval)
        st.rerun()


def render_dashboard_view(manager, history_df, status_df, alerts):
    """Render main dashboard view"""
    
    # KPI Metrics
    render_kpi_metrics(manager)
    
    st.markdown("---")
    
    # Alerts
    render_alert_panel(alerts)
    
    st.markdown("---")
    
    # Main charts
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("📈 Real-time Monitoring")
        if not history_df.empty:
            plot_realtime_dashboard(history_df)
        else:
            st.info("Click **Step** to generate data")
    
    with col2:
        st.subheader("🏥 Motor Health")
        plot_health_bars(status_df)
    
    st.markdown("---")
    
    # Simulation info and fleet overview
    col1, col2 = st.columns(2)
    
    with col1:
        render_simulation_info(manager)
    
    with col2:
        render_fleet_overview(status_df)


def render_analysis_view(manager, history_df, status_df):
    """Render detailed analysis view"""
    
    st.subheader("🔬 Detailed Analysis")
    
    if history_df.empty:
        st.info("No data available for analysis. Click **Step** to generate data.")
        return
    
    # Sensor grid
    st.markdown("### Sensor Time Series")
    plot_sensor_grid(history_df)
    
    st.markdown("---")
    
    # Correlation and scatter
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Correlation Analysis")
        plot_correlation_heatmap(history_df)
    
    with col2:
        st.markdown("### Health vs Vibration")
        plot_health_vs_sensor(history_df, sensor="vibration")
    
    st.markdown("---")
    
    # Additional scatter plots
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Health vs Temperature")
        plot_health_vs_sensor(history_df, sensor="temperature")
    
    with col2:
        st.markdown("### Health vs Current")
        plot_health_vs_sensor(history_df, sensor="current")


def render_advanced_view(manager, history_df):
    """Render advanced features view (Phase 6 improvements)"""
    
    st.subheader("🚀 Advanced Features - Phase 6 Improvements")
    
    if history_df.empty:
        st.info("No data available. Click **Step** to generate data.")
        return
    
    st.markdown("""
    This view showcases the industrial-grade improvements:
    - **Stochastic Degradation**: Non-linear burst damage
    - **Asynchronous Sensors**: Different response times
    - **Operating Regimes**: Idle/Normal/Peak modes
    - **Sensor Imperfections**: Realistic failures
    - **Maintenance Events**: Intervention modeling
    """)
    
    st.markdown("---")
    
    # Stochastic degradation
    st.markdown("### 1️⃣ Stochastic Degradation with Burst Events")
    st.markdown("Notice the **jagged health curves** with occasional sharp drops (red X markers)")
    plot_health_with_bursts(history_df)
    
    st.markdown("---")
    
    # Asynchronous response
    st.markdown("### 2️⃣ Asynchronous Sensor Response")
    st.markdown("**Vibration** reacts immediately, **Current** lags slightly, **Temperature** lags significantly")
    plot_sensor_response_lag(history_df)
    
    st.markdown("---")
    
    # Operating regimes
    st.markdown("### 3️⃣ Operating Regime Transitions")
    st.markdown("Watch how **Current** and **Temperature** respond to regime changes")
    plot_operating_regimes(history_df)
    
    st.markdown("---")
    
    # Maintenance events
    st.markdown("### 4️⃣ Maintenance Events")
    st.markdown("Green stars (⭐) indicate maintenance interventions with partial health recovery")
    plot_maintenance_events(history_df)
    
    st.markdown("---")
    
    # Sensor imperfections
    st.markdown("### 5️⃣ Sensor Imperfections")
    st.markdown("Red X markers show **missing data** from sensor failures")
    plot_sensor_quality_indicators(history_df)


def render_fleet_view(manager, status_df):
    """Render fleet status view"""
    
    st.subheader("🏭 Fleet Status Overview")
    
    if status_df.empty:
        st.info("No fleet data available")
        return
    
    # Fleet overview
    render_fleet_overview(status_df)
    
    st.markdown("---")
    
    # Health bars
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### Motor Health Bars")
        plot_health_bars(status_df)
    
    with col2:
        st.markdown("### Alerts")
        alerts = manager.get_alerts()
        render_alert_panel(alerts)
    
    st.markdown("---")
    
    # Detailed table
    st.markdown("### Motor Status Table")
    render_motor_table(status_df)


def render_data_view(history_df, status_df):
    """Render raw data view"""
    
    st.subheader("📊 Raw Data")
    
    tab1, tab2 = st.tabs(["History Data", "Current Status"])
    
    with tab1:
        st.markdown("### Historical Sensor Data")
        
        if history_df.empty:
            st.info("No historical data available")
        else:
            # Data info
            st.write(f"**Shape:** {history_df.shape[0]} rows × {history_df.shape[1]} columns")
            st.write(f"**Time Range:** {history_df['time'].min()} to {history_df['time'].max()}")
            
            # Show data
            st.dataframe(history_df, use_container_width=True, height=400)
            
            # Download button
            csv = history_df.to_csv(index=False)
            st.download_button(
                label="📥 Download History CSV",
                data=csv,
                file_name="simulation_history.csv",
                mime="text/csv"
            )
    
    with tab2:
        st.markdown("### Current Motor Status")
        
        if status_df.empty:
            st.info("No status data available")
        else:
            st.dataframe(status_df, use_container_width=True)
            
            # Download button
            csv = status_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Status CSV",
                data=csv,
                file_name="motor_status.csv",
                mime="text/csv"
            )


# Footer
def render_footer():
    """Render footer"""
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: gray; padding: 20px;'>
        🏭 Industrial Predictive Maintenance Simulator | 
        Built with Streamlit & Physics-Based Modeling | 
        © 2026
        </div>
        """,
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    try:
        main()
        render_footer()
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        st.exception(e)
        st.info("Please check the logs or refresh the page.")
