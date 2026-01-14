"""
Industrial Predictive Maintenance Simulator - Hugging Face Streamlit Space
Entry point for Hugging Face deployment
"""
import sys
import os

# Add project root and ui directory to path
project_root = os.path.dirname(os.path.abspath(__file__))
ui_path = os.path.join(project_root, 'ui')
if project_root not in sys.path:
    sys.path.insert(0, project_root)
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

# Import the app components
import streamlit as st

# Must be the first Streamlit command
st.set_page_config(
    page_title="Industrial Maintenance Simulator",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Now import app functions (after page config)
try:
    from ui.app import main as run_main_app, render_footer, initialize_session_state
    
    # Run the application
    try:
        initialize_session_state()
        run_main_app()
        render_footer()
    except Exception as e:
        st.error(f"❌ Application Error: {str(e)}")
        st.exception(e)
        st.info("Please refresh the page or check the logs.")
        
except ImportError as e:
    st.error(f"❌ Import Error: {str(e)}")
    st.info("Unable to load the application. Please check the deployment logs.")
