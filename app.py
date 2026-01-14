"""
Industrial Predictive Maintenance Simulator - Hugging Face Streamlit Space
Entry point for Hugging Face deployment
"""
import sys
import os

# Add ui directory to path for imports
ui_path = os.path.join(os.path.dirname(__file__), 'ui')
if ui_path not in sys.path:
    sys.path.insert(0, ui_path)

# Import and run the main app
from ui.app import main

if __name__ == "__main__":
    main()
