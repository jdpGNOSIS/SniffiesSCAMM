$shell = New-Object -ComObject WScript.Shell
$desktop = "C:\Users\DEZRA\OneDrive\Desktop"

$shortcutPath = "$desktop\Sniffies Command Station.lnk"
$iconPath = "C:\Users\DEZRA\OneDrive\Desktop\area51\SniffiesSCAMM\gui\assets\sniffies.ico"
$scriptPath = "C:\Users\DEZRA\OneDrive\Desktop\area51\SniffiesSCAMM\gui\main.py"

$shortcut = $shell.CreateShortcut($shortcutPath)
$batPath = "C:\Users\DEZRA\OneDrive\Desktop\area51\SniffiesSCAMM\gui\Sniffies Command Station.bat"
$shortcut.TargetPath = "$batPath"
$shortcut.Arguments = ""
$shortcut.WorkingDirectory = "C:\Users\DEZRA\OneDrive\Desktop\area51\SniffiesSCAMM"
$shortcut.Description = "Sniffies Command Station - Multi-Agent Orchestrator"
$shortcut.IconLocation = "$iconPath, 0"

$shortcut.Save()
Write-Host "Shortcut created:"
Write-Host "  Path: $shortcutPath"
Write-Host "  Icon: $iconPath"
Write-Host "  Target: python.exe `"$scriptPath`""
