@echo off
echo ===================================================
echo School Result Analysis System - Local Runner
echo ===================================================

echo.
echo [1/3] Checking for existing server on port 8000...
FOR /F "tokens=5" %%T IN ('netstat -a -n -o ^| findstr :8000') DO (
    echo Stopping process with PID: %%T
    TaskKill.exe /F /PID %%T 2>NUL
)

echo.
echo [2/3] Starting backend server...
cd backend
:: Open the server in a new command prompt window so it doesn't block the script
start "SRAS Backend Server" cmd /k "venv\Scripts\uvicorn.exe app.main:app --host 127.0.0.1 --port 8000 --reload"

echo.
echo [3/3] Waiting for server initialization...
timeout /t 3 /nobreak > NUL

echo.
echo Opening dashboard in your default browser...
start http://127.0.0.1:8000/

echo.
echo Done! Keep the newly opened command prompt window running.
echo To shut down, close the server window or run this script again.
pause
