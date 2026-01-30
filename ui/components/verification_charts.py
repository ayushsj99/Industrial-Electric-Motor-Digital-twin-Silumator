"""
Data Verification Charts - Display per-motor time series for validation
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Dict


def render_data_verification_view(history_df: pd.DataFrame, manager):
    """
    Render comprehensive data verification view with per-motor analysis
    """
    if history_df.empty:
        st.warning("No data available for verification. Generate data first.")
        return
    
    st.header("📊 Data Verification Dashboard")
    st.markdown("**Review generated data quality before download**")
    
    # Overview metrics
    total_records = len(history_df)
    unique_motors = history_df['motor_id'].nunique()
    unique_cycles = history_df['cycle_id'].nunique() if 'cycle_id' in history_df.columns else 1
    time_span = history_df['time'].max() - history_df['time'].min()
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Records", f"{total_records:,}")
    with col2:
        st.metric("Motors", unique_motors)
    with col3:
        st.metric("Cycles per Motor", unique_cycles // unique_motors if unique_motors > 0 else 0)
    with col4:
        st.metric("Time Span", f"{time_span:,} steps")
    
    st.markdown("---")
    
    # Motor selector for detailed view
    motor_ids = sorted(history_df['motor_id'].unique())
    selected_motor = st.selectbox(
        "🔍 Select Motor for Detailed Analysis:",
        options=motor_ids,
        format_func=lambda x: f"Motor {x}"
    )
    
    # Filter data for selected motor
    motor_df = history_df[history_df['motor_id'] == selected_motor].copy()
    motor_df = motor_df.sort_values('time')
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs([
        "📈 Health & Metrics", 
        "🔧 Maintenance Cycles", 
        "📊 Sensor Responses", 
        "🏭 All Motors Overview"
    ])
    
    with tab1:
        render_motor_health_analysis(motor_df, selected_motor)
    
    with tab2:
        render_maintenance_cycle_analysis(motor_df, selected_motor)
    
    with tab3:
        render_sensor_response_analysis(motor_df, selected_motor)
    
    with tab4:
        render_fleet_comparison(history_df)


def render_motor_health_analysis(motor_df: pd.DataFrame, motor_id: int):
    """Render detailed health analysis for a specific motor"""
    st.subheader(f"🏥 Motor {motor_id} Health Analysis")
    
    if motor_df.empty:
        st.warning("No data available for this motor")
        return
    
    # Health state visualization
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=[
            "Health Progression Over Time",
            "Temperature vs Vibration",
            "Health Distribution by Cycle",
            "Critical Events Timeline"
        ],
        specs=[[{"secondary_y": True}, {}],
               [{}, {}]]
    )
    
    # Plot 1: Health progression
    if 'cycle_id' in motor_df.columns:
        colors = motor_df['cycle_id'].astype(int)  # Convert to int for numeric color mapping
        fig.add_trace(
            go.Scatter(
                x=motor_df['time'], 
                y=motor_df['motor_health'],
                mode='lines+markers',
                marker=dict(
                    color=colors,
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title="Cycle ID", x=0.45)
                ),
                name="Health",
                line=dict(width=2)
            ),
            row=1, col=1
        )
    else:
        fig.add_trace(
            go.Scatter(
                x=motor_df['time'], 
                y=motor_df['motor_health'],
                mode='lines',
                name="Health",
                line=dict(color='red', width=2)
            ),
            row=1, col=1
        )
    
    # Add health thresholds
    fig.add_hline(y=0.7, line_dash="dash", line_color="green", 
                  annotation_text="Healthy", row=1, col=1)
    fig.add_hline(y=0.3, line_dash="dash", line_color="orange", 
                  annotation_text="Warning", row=1, col=1)
    fig.add_hline(y=0.1, line_dash="dash", line_color="red", 
                  annotation_text="Critical", row=1, col=1)
    
    # Plot 2: Temperature vs Vibration scatter
    fig.add_trace(
        go.Scatter(
            x=motor_df['temperature'],
            y=motor_df['vibration'],
            mode='markers',
            marker=dict(
                color=motor_df['motor_health'],
                colorscale='RdYlGn',
                size=6,
                showscale=True,
                colorbar=dict(title="Health", x=1.05)
            ),
            name="Temp vs Vib",
            text=[f"Time: {t}" for t in motor_df['time']],
            hovertemplate="<b>Temperature:</b> %{x:.2f}<br>" +
                         "<b>Vibration:</b> %{y:.2f}<br>" +
                         "<b>Health:</b> %{marker.color:.3f}<br>" +
                         "%{text}<extra></extra>"
        ),
        row=1, col=2
    )
    
    # Plot 3: Health distribution by cycle
    if 'cycle_id' in motor_df.columns:
        cycles = motor_df['cycle_id'].unique()
        for cycle in sorted(cycles):
            cycle_data = motor_df[motor_df['cycle_id'] == cycle]
            fig.add_trace(
                go.Histogram(
                    x=cycle_data['motor_health'],
                    name=f"Cycle {cycle}",
                    opacity=0.7,
                    nbinsx=20
                ),
                row=2, col=1
            )
    
    # Plot 4: Critical events timeline
    maintenance_events = motor_df[motor_df.get('maintenance_event', '') == 'automatic_maintenance']
    if not maintenance_events.empty:
        fig.add_trace(
            go.Scatter(
                x=maintenance_events['time'],
                y=[1] * len(maintenance_events),
                mode='markers',
                marker=dict(
                    color='red',
                    size=15,
                    symbol='diamond'
                ),
                name="Maintenance Events",
                text=[f"Maintenance at time {t}" for t in maintenance_events['time']],
                hovertemplate="<b>Maintenance Event</b><br>Time: %{x}<extra></extra>"
            ),
            row=2, col=2
        )
    
    # Add critical health events
    critical_events = motor_df[motor_df['motor_health'] <= 0.1]
    if not critical_events.empty:
        fig.add_trace(
            go.Scatter(
                x=critical_events['time'],
                y=[0.5] * len(critical_events),
                mode='markers',
                marker=dict(
                    color='orange',
                    size=10,
                    symbol='triangle-up'
                ),
                name="Critical Health",
                text=[f"Health: {h:.3f}" for h in critical_events['motor_health']],
                hovertemplate="<b>Critical Health</b><br>Time: %{x}<br>Health: %{text}<extra></extra>"
            ),
            row=2, col=2
        )
    
    fig.update_layout(
        height=700,
        title=f"Motor {motor_id} Comprehensive Analysis",
        showlegend=True
    )
    
    fig.update_xaxes(title_text="Time Steps", row=1, col=1)
    fig.update_yaxes(title_text="Health Level", row=1, col=1)
    fig.update_xaxes(title_text="Temperature", row=1, col=2)
    fig.update_yaxes(title_text="Vibration", row=1, col=2)
    fig.update_xaxes(title_text="Health Level", row=2, col=1)
    fig.update_yaxes(title_text="Frequency", row=2, col=1)
    fig.update_xaxes(title_text="Time Steps", row=2, col=2)
    fig.update_yaxes(title_text="Event Type", row=2, col=2)
    
    st.plotly_chart(fig, use_container_width=True)


def render_maintenance_cycle_analysis(motor_df: pd.DataFrame, motor_id: int):
    """Render maintenance cycle analysis"""
    st.subheader(f"🔧 Motor {motor_id} Maintenance Cycle Analysis")
    
    if 'cycle_id' not in motor_df.columns:
        st.warning("Cycle tracking not available in this dataset")
        return
    
    cycles = sorted(motor_df['cycle_id'].unique())
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📊 Cycle Statistics**")
        
        cycle_stats = []
        for cycle in cycles:
            cycle_data = motor_df[motor_df['cycle_id'] == cycle]
            stats = {
                'Cycle': cycle,
                'Duration': len(cycle_data),
                'Min Health': cycle_data['motor_health'].min(),
                'Max Health': cycle_data['motor_health'].max(),
                'Health Range': cycle_data['motor_health'].max() - cycle_data['motor_health'].min(),
                'Avg Temp': cycle_data['temperature'].mean(),
                'Max Vibration': cycle_data['vibration'].max()
            }
            cycle_stats.append(stats)
        
        stats_df = pd.DataFrame(cycle_stats)
        st.dataframe(stats_df, use_container_width=True)
    
    with col2:
        st.markdown("**🎯 Cycle Quality Metrics**")
        
        # Calculate quality metrics
        quality_metrics = []
        for cycle in cycles:
            cycle_data = motor_df[motor_df['cycle_id'] == cycle]
            
            # Check if cycle reached critical
            reached_critical = (cycle_data['motor_health'] <= 0.1).any()
            
            # Check for smooth degradation (no sudden jumps)
            health_diff = cycle_data['motor_health'].diff().abs()
            smooth_degradation = health_diff.mean() < 0.05
            
            # Check maintenance recovery
            maintenance_events = cycle_data[cycle_data.get('maintenance_event', '') == 'automatic_maintenance']
            has_maintenance = not maintenance_events.empty
            
            quality = {
                'Cycle': cycle,
                'Reached Critical': '✅' if reached_critical else '❌',
                'Smooth Degradation': '✅' if smooth_degradation else '❌',
                'Has Maintenance': '✅' if has_maintenance else '❌',
                'Quality Score': sum([reached_critical, smooth_degradation, has_maintenance])
            }
            quality_metrics.append(quality)
        
        quality_df = pd.DataFrame(quality_metrics)
        st.dataframe(quality_df, use_container_width=True)
    
    # Cycle overlay chart
    st.markdown("**📈 All Cycles Overlay**")
    
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set1
    for i, cycle in enumerate(cycles):
        cycle_data = motor_df[motor_df['cycle_id'] == cycle].copy()
        # Normalize time to start from 0 for each cycle
        cycle_data['relative_time'] = cycle_data['time'] - cycle_data['time'].min()
        
        fig.add_trace(
            go.Scatter(
                x=cycle_data['relative_time'],
                y=cycle_data['motor_health'],
                name=f"Cycle {cycle}",
                line=dict(color=colors[i % len(colors)], width=2),
                mode='lines'
            )
        )
    
    fig.add_hline(y=0.1, line_dash="dash", line_color="red", 
                  annotation_text="Critical Threshold")
    
    fig.update_layout(
        title="Health Progression - All Cycles Normalized",
        xaxis_title="Relative Time Steps",
        yaxis_title="Health Level",
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_sensor_response_analysis(motor_df: pd.DataFrame, motor_id: int):
    """Render sensor response analysis"""
    st.subheader(f"📊 Motor {motor_id} Sensor Response Analysis")
    
    # Multi-sensor time series
    sensor_cols = ['temperature', 'vibration', 'current', 'acoustic']
    available_sensors = [col for col in sensor_cols if col in motor_df.columns]
    
    if not available_sensors:
        st.warning("No sensor data available")
        return
    
    fig = make_subplots(
        rows=len(available_sensors), cols=1,
        shared_xaxes=True,
        subplot_titles=[f"{sensor.title()} Sensor" for sensor in available_sensors],
        vertical_spacing=0.05
    )
    
    for i, sensor in enumerate(available_sensors):
        fig.add_trace(
            go.Scatter(
                x=motor_df['time'],
                y=motor_df[sensor],
                name=sensor.title(),
                line=dict(width=2),
                hovertemplate=f"<b>{sensor.title()}</b><br>" +
                             "Time: %{x}<br>" +
                             f"{sensor.title()}: %{{y:.3f}}<br>" +
                             "<extra></extra>"
            ),
            row=i+1, col=1
        )
        
        fig.update_yaxes(title_text=sensor.title(), row=i+1, col=1)
    
    fig.update_xaxes(title_text="Time Steps", row=len(available_sensors), col=1)
    fig.update_layout(
        height=150 * len(available_sensors),
        title=f"Motor {motor_id} - All Sensor Responses",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Sensor correlations
    st.markdown("**🔗 Sensor Correlation Analysis**")
    
    correlation_data = motor_df[available_sensors + ['motor_health']].corr()
    
    fig_corr = px.imshow(
        correlation_data,
        text_auto=True,
        aspect="auto",
        color_continuous_scale="RdBu_r",
        title="Sensor and Health Correlations"
    )
    
    st.plotly_chart(fig_corr, use_container_width=True)


def render_fleet_comparison(history_df: pd.DataFrame):
    """Render fleet-wide comparison view"""
    st.subheader("🏭 Fleet-Wide Data Overview")
    
    motor_ids = sorted(history_df['motor_id'].unique())
    
    # Fleet health comparison
    fig = go.Figure()
    
    colors = px.colors.qualitative.Set1
    for i, motor_id in enumerate(motor_ids):
        motor_data = history_df[history_df['motor_id'] == motor_id].sort_values('time')
        
        fig.add_trace(
            go.Scatter(
                x=motor_data['time'],
                y=motor_data['motor_health'],
                name=f"Motor {motor_id}",
                line=dict(color=colors[i % len(colors)], width=2),
                mode='lines'
            )
        )
    
    fig.add_hline(y=0.1, line_dash="dash", line_color="red", 
                  annotation_text="Critical Threshold")
    fig.add_hline(y=0.3, line_dash="dash", line_color="orange", 
                  annotation_text="Warning Threshold")
    fig.add_hline(y=0.7, line_dash="dash", line_color="green", 
                  annotation_text="Healthy Threshold")
    
    fig.update_layout(
        title="Fleet Health Comparison - All Motors",
        xaxis_title="Time Steps",
        yaxis_title="Health Level",
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Fleet statistics summary
    st.markdown("**📋 Fleet Summary Statistics**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fleet_stats = []
        for motor_id in motor_ids:
            motor_data = history_df[history_df['motor_id'] == motor_id]
            stats = {
                'Motor ID': motor_id,
                'Records': len(motor_data),
                'Min Health': motor_data['motor_health'].min(),
                'Max Health': motor_data['motor_health'].max(),
                'Avg Health': motor_data['motor_health'].mean(),
                'Health Variance': motor_data['motor_health'].var()
            }
            fleet_stats.append(stats)
        
        fleet_df = pd.DataFrame(fleet_stats)
        st.dataframe(fleet_df, use_container_width=True)
    
    with col2:
        # Data quality metrics
        quality_stats = []
        for motor_id in motor_ids:
            motor_data = history_df[history_df['motor_id'] == motor_id]
            
            # Check cycles if available
            cycles = motor_data['cycle_id'].nunique() if 'cycle_id' in motor_data.columns else 1
            
            # Check maintenance events
            maintenance_events = motor_data[motor_data.get('maintenance_event', '') == 'automatic_maintenance']
            maintenance_count = len(maintenance_events)
            
            quality = {
                'Motor ID': motor_id,
                'Cycles': cycles,
                'Maintenance Events': maintenance_count,
                'Data Completeness': f"{(motor_data.notna().sum().sum() / (len(motor_data) * len(motor_data.columns))) * 100:.1f}%",
                'Time Span': motor_data['time'].max() - motor_data['time'].min()
            }
            quality_stats.append(quality)
        
        quality_df = pd.DataFrame(quality_stats)
        st.dataframe(quality_df, use_container_width=True)