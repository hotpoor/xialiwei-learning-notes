# Read-only host checks. Run in Windows PowerShell on the RTX 3090 PC.
# Does not install software, change settings, or upload results.
$ErrorActionPreference = 'Continue'

Write-Output 'Windows version'
Get-CimInstance Win32_OperatingSystem |
    Select-Object Caption, Version, BuildNumber |
    Format-List

Write-Output 'System RAM (GB)'
$computer = Get-CimInstance Win32_ComputerSystem
[math]::Round($computer.TotalPhysicalMemory / 1GB, 1)

Write-Output 'Disk free space (GB)'
Get-PSDrive -PSProvider FileSystem |
    Select-Object Name, @{Name='FreeGB';Expression={[math]::Round($_.Free / 1GB, 1)}} |
    Format-Table -AutoSize

Write-Output 'NVIDIA GPU and driver'
if (Get-Command nvidia-smi -ErrorAction SilentlyContinue) {
    & nvidia-smi --query-gpu=name,driver_version,memory.total,memory.free --format=csv
} else {
    Write-Output 'nvidia-smi not found. Driver status has not been verified.'
}

Write-Output 'WSL version'
if (Get-Command wsl.exe -ErrorAction SilentlyContinue) {
    & wsl.exe --version
    Write-Output 'WSL distributions'
    & wsl.exe --list --verbose
} else {
    Write-Output 'wsl.exe not found. WSL has not been verified.'
}
