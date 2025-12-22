@echo off
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

call venv\Scripts\activate

echo Installing/Updating dependencies...
venv\Scripts\python -m pip install -r requirements.txt
echo Checking Playwright browsers...
venv\Scripts\python -m playwright install

echo Starting Social Bot...
venv\Scripts\python main.py
pause
