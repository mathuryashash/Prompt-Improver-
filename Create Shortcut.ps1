# Create Shortcut.ps1
# Run ONCE to put a PromptImprover shortcut on your Desktop.
# After that, double-click the shortcut to start the app with no terminal window.

$projectRoot  = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonw      = Join-Path $projectRoot ".venv\Scripts\pythonw.exe"
$runScript    = Join-Path $projectRoot "run.pyw"
$desktop      = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktop "PromptImprover.lnk"

if (-not (Test-Path $pythonw)) {
    Write-Error "pythonw.exe not found at: $pythonw"
    Write-Host "Set up the virtual environment first: python -m venv .venv && pip install -r requirements.txt"
    exit 1
}

$shell    = New-Object -ComObject WScript.Shell
$lnk      = $shell.CreateShortcut($shortcutPath)
$lnk.TargetPath       = $pythonw
$lnk.Arguments        = "`"$runScript`""
$lnk.WorkingDirectory = $projectRoot
$lnk.WindowStyle      = 7
$lnk.Description      = "PromptImprover - AI prompt optimizer"

$icoPath = Join-Path $projectRoot "assets\icon.ico"
if (Test-Path $icoPath) { $lnk.IconLocation = $icoPath }

$lnk.Save()

Write-Host ""
Write-Host "Shortcut created: $shortcutPath"
Write-Host "Double-click PromptImprover on your Desktop to launch."
Write-Host "The app starts silently and lives in the system tray."
