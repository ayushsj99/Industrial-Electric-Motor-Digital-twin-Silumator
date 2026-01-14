"""
Industrial Predictive Maintenance Simulator - Hugging Face Streamlit Space
Entry point for Hugging Face deployment
"""
import sys
import os

# Add project root and ui directory to path
project_root = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(project_root, 'ui')
sys.path.insert(0, project_root)
sys.path.insert(0, ui_path)

import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="Industrial Maintenance Simulator",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Debug: Show what we're trying to import
st.write("🔍 Debug Info:")
st.write(f"Project root: {project_root}")
st.write(f"UI path: {ui_path}")
st.write(f"sys.path: {sys.path[:3]}")

# Try to import
try:
    st.write("Attempting to import from ui.app...")
    from ui.app import main as run_main_app, render_footer, initialize_session_state
    st.write("✅ Import successful!")
    
    # Run the application
    initialize_session_state()
    run_main_app()
    render_footer()
    
except Exception as e:
    st.error(f"❌ Error: {str(e)}")
    st.exception(e)
    
    # Try to show directory structure
    st.write("📂 Directory contents:")
    st.write(f"Root files: {os.listdir(project_root)[:10]}")
    if os.path.exists(ui_path):
        st.write(f"UI files: {os.listdir(ui_path)}")

