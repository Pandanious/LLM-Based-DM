@echo off
set ROOT=%~dp0
set VENV=%ROOT%.venv\Scripts\activate

echo Launching Streamlit...
start "Streamlit" cmd /k "cd /d %ROOT% && call %VENV% && streamlit run src/UI/streamlit_webapp.py"

echo Launching ngrok...
start "ngrok" cmd /k "cd /d %ROOT% && ngrok http 8501 --traffic-policy-file=src/UI/policy.yaml"

echo Launched. Close the Streamlit/ngrok windows to stop them.
