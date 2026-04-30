import sys
import os
from pathlib import Path

# Add backend to path
backend_path = os.path.join(os.getcwd(), "backend")
if backend_path not in sys.path:
    sys.path.append(backend_path)

from config import settings

print(f"CWD: {os.getcwd()}")
print(f"BASE_DIR: {settings.BASE_DIR}")
print(f"DATA_DIR: {settings.DATA_DIR}")
print(f"LOG_FILE: {settings.LOG_FILE}")

# Check if DATA_DIR is absolute
if settings.DATA_DIR.is_absolute():
    print("SUCCESS: DATA_DIR is absolute.")
else:
    print("FAILURE: DATA_DIR is still relative.")
