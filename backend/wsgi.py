import sys
import os

# Add the current directory to the path so that imports work correctly
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app

if __name__ == "__main__":
    app.run()
