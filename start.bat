@echo off
echo ========================================================
echo Starting Smart Civic AI System...
echo ========================================================

echo Activating virtual environment and starting server...
call .\venv\Scripts\activate.bat
python run.py
pause
