@echo off
echo 🚀 Steam Screenshot Utils GUI
echo =============================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.7+ and try again
    pause
    exit /b 1
)

REM Check if required packages are installed
echo Checking dependencies...
python -c "import customtkinter, requests, docopt" >nul 2>&1
if errorlevel 1 (
    echo Installing required packages...
    pip install customtkinter Pillow requests docopt
    if errorlevel 1 (
        echo ❌ Failed to install dependencies
        echo Please run: pip install customtkinter Pillow requests docopt
        pause
        exit /b 1
    )
)

echo ✅ Dependencies OK
echo.

REM Launch the GUI
echo Starting GUI...
python run_gui.py

pause
