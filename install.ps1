# Sets up Jarvis on Windows 10/11: the Python environment and a Start Menu shortcut. Safe to run again.
# Run it from PowerShell in this folder:  powershell -ExecutionPolicy Bypass -File .\install.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "Installing uv (the Python package manager Jarvis uses)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
}
if (-not (Test-Path .venv)) { uv venv --python 3.13 .venv }
uv pip install -q --python .venv\Scripts\python.exe -r requirements.txt
uv pip install -q --python .venv\Scripts\python.exe --no-deps openwakeword  # (its tflite dependency has no current wheels)

$config = Join-Path $env:APPDATA "Jarvis"
New-Item -ItemType Directory -Force $config | Out-Null

# Start Menu shortcut; pythonw runs it without a console window
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path ([Environment]::GetFolderPath("Programs")) "Jarvis.lnk"))
$shortcut.TargetPath = (Resolve-Path .venv\Scripts\pythonw.exe).Path
$shortcut.Arguments = "`"$PSScriptRoot\jarvis.py`""
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.IconLocation = "$PSScriptRoot\icon.ico"
$shortcut.Description = 'Voice assistant (say "Hey Jarvis")'
$shortcut.Save()

if (-not (Test-Path (Join-Path $config "env"))) {
    Write-Host "Next: put your Google AI Studio key in $config\env as  GEMINI_API_KEY=..."
}
Write-Host "Installed. Start Jarvis from the Start Menu (Jarvis)."
