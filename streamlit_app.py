"""
Hugging Face Spaces Entry Point
This file is automatically detected by Streamlit and Hugging Face Spaces
"""
import sys
import os

# Add paths
project_root = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(project_root, 'ui')
sys.path.insert(0, project_root)
sys.path.insert(0, ui_path)

import streamlit as st

# Set page config first
st.set_page_config(
    page_title="Industrial Maintenance Simulator",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import and run the app
try:
    from ui.app import main as run_main_app, render_footer, initialize_session_state
    
    initialize_session_state()
    run_main_app()
    render_footer()
    
except Exception as e:
    st.error(f"❌ Application Error: {str(e)}")
    st.exception(e)
    st.info("Please check the logs or refresh the page.")
