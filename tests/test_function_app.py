# tests/test_function_app.py
import os
import sys

# 將專案根目錄加入 Python 路徑
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from importlib import import_module


def test_can_import_function_app():
    pkg = import_module("SchedulerAgent_function")
    assert hasattr(pkg, "function_app"), "SchedulerAgent_function 應該要有 function_app 屬性"

    from SchedulerAgent_function import function_app
    assert function_app is not None
