@echo off
set ROOT=%~dp0
call "%ROOT%\.venv\Scripts\activate"
python -m pytest src/tests
