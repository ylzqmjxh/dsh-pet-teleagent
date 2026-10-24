@echo off
setlocal
cd /d "%~dp0"

rem Prefer pythonw (no console window); fall back to bundled runtime path.
where pythonw >nul 2>nul
if %errorlevel%==0 (
    start "" pythonw -m pet
) else (
    start "" "C:\Users\ylzqm\.local\share\TeleAgent\runtimes\python\pythonw.exe" -m pet
)

rem TeleAgent island-state watcher: starts together with the pet.
rem Single-instance guarded inside the watcher; extra starts are no-ops.
start "" /b "C:\Users\ylzqm\.local\share\TeleAgent\runtimes\python\pythonw.exe" "C:\Users\ylzqm\.config\TeleAgent\users\v1_public_1903019940692033539\skills\dsh-pet-bridge\scripts\teleagent_watcher.py"

endlocal