@echo off
rem DraveWriter starten vanuit de broncode (de exe staat in dist\DraveWriter).
cd /d "%~dp0"
if exist ".venv\Scripts\pythonw.exe" ( start "" ".venv\Scripts\pythonw.exe" dravewriter.py & exit /b )
for %%V in (3.13 3.12 3.11) do (
  py -%%V -c "import PyQt6" >nul 2>&1 && ( start "" pyw -%%V dravewriter.py & exit /b )
)
echo PyQt6 niet gevonden. Bouw eerst de exe met bouw-exe.bat.
pause
