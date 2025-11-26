@echo off
@echo off
echo Starting Streamlit + ngrok with separate terminals...
echo.

REM Change to project root
cd /d H:\Python\Agentic-Tutorial

REM Activate virtual environment
call .venv\Scripts\activate

echo Launching Streamlit...
start "Streamlit" cmd /k "streamlit run src/UI/streamlit_webapp.py"
echo Streamlit window launched.
echo.

timeout /t 2 >nul

echo Launching ngrok with policy...
start "ngrok" cmd /k "ngrok http 8501 --traffic-policy-file=src/UI/policy.yaml"
echo ngrok window launched.
echo.

echo All systems running. Close this window anytime.
pause
