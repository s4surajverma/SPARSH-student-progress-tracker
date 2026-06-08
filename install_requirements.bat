@echo off
TITLE SPARSH - Install Requirements
COLOR 0A

echo ==================================================
echo SPARSH Setup - Installing Requirements
echo ==================================================
echo.

:: 1. Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not added to your system PATH.
    echo Please install Python 3.10 or newer from https://www.python.org/downloads/
    echo Make sure to check the box "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: 2. Create virtual environment in the backend folder if it doesn't exist
cd backend

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo [INFO] Creating Python virtual environment...
    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
) ELSE (
    echo [INFO] Virtual environment already exists.
)

:: 3. Activate virtual environment
call venv\Scripts\activate.bat

:: 4. Upgrade pip
echo.
echo [INFO] Upgrading pip to the latest version...
python -m pip install --upgrade pip

:: 5. Install requirements
echo.
echo [INFO] Installing required Python packages...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to install dependencies. Check your internet connection or requirements.txt.
    pause
    exit /b 1
)

:: 6. Run database migrations
echo.
echo [INFO] Setting up the local database...
alembic upgrade head
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Failed to run database migrations.
    pause
    exit /b 1
)

echo.
echo ==================================================
echo [SUCCESS] All requirements installed successfully!
echo The database is initialized and ready.
echo.
echo You can now run the application by double-clicking 'run_locally.bat'
echo ==================================================
pause
