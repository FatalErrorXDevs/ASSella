import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from PyQt6.QtWidgets import QApplication
from core.tasks.generate_achievements_task import GenerateAchievementsTask

def test_achievements_task():
    # Setup PyQt Application
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
        
    task = GenerateAchievementsTask()
    
    # Check that task has correct signals
    assert hasattr(task, 'progress'), "Task missing progress signal"
    assert hasattr(task, 'progress_percentage'), "Task missing progress_percentage signal"
    assert hasattr(task, 'completed'), "Task missing completed signal"
    assert hasattr(task, 'error'), "Task missing error signal"
    
    # Run task without credentials to ensure it emits error/completion correctly
    emitted_error = []
    emitted_completed = []
    
    task.error.connect(lambda msg: emitted_error.append(msg))
    task.completed.connect(lambda res: emitted_completed.append(res))
    
    # We clear steam_username / steam_password in settings first if any exists,
    # or verify what it returns.
    from utils.settings import get_settings
    settings = get_settings()
    orig_user = settings.value("steam_username")
    orig_pass = settings.value("steam_password")
    
    settings.remove("steam_username")
    settings.remove("steam_password")
    
    try:
        res = task.run("440") # Run for Team Fortress 2
        print(f"Task result: {res}")
        
        assert res["success"] is False, "Task should fail without credentials"
        assert "Steam credentials not configured" in res["message"], f"Unexpected message: {res['message']}"
        assert len(emitted_error) == 1, "Task should emit exactly one error"
        assert len(emitted_completed) == 1, "Task should emit exactly one completion"
        
        print("Achievements task validation test passed successfully!")
        
    finally:
        # Restore settings
        if orig_user is not None:
            settings.setValue("steam_username", orig_user)
        if orig_pass is not None:
            settings.setValue("steam_password", orig_pass)

if __name__ == "__main__":
    test_achievements_task()
