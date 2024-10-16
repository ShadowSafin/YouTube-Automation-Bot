@echo off
REM Create a virtual environment
python -m venv venv

REM Activate the virtual environment (Windows)
call venv\Scripts\activate

REM Install required packages from requirements.txt
pip install -r requirements.txt

REM Run PyInstaller to create the executable
pyinstaller --name YouTubeAutomation --noconsole --icon=icon.ico --onefile --add-data "client_secret.json:." --add-data "credentials.json:." --add-data "templates:templates" runme.py

REM Pause to keep the window open after execution
pause
