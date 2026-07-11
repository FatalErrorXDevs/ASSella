import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from PyQt6.QtWidgets import QApplication
from ui.dialogs.settings import SettingsDialog

def test_settings_init():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        
    try:
        print("Instantiating SettingsDialog...")
        dialog = SettingsDialog()
        print("SettingsDialog instantiated successfully!")
    except Exception as e:
        import traceback
        print("CRASH TRACEBACK:")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    test_settings_init()
