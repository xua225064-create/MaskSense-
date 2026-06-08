Write-Host "Downloading Ollama installer from GitHub..."
$url = "https://github.com/ollama/ollama/releases/download/v0.1.47/OllamaSetup.exe"
$temp = $env:TEMP
$output = Join-Path $temp "OllamaSetup.exe"

Write-Host "URL: $url"
Write-Host "Saving to: $output"
Write-Host ""

$ProgressPreference = 'SilentlyContinue'

try {
    Invoke-WebRequest -Uri $url -OutFile $output -TimeoutSec 300
    $size = (Get-Item $output).Length / (1024*1024)
    Write-Host "Download complete! Size: $([math]::Round($size,2)) MB"
    Write-Host ""
    Write-Host "Starting Ollama installer..."
    Start-Process $output
    Write-Host "Installer launched! Follow the wizard to complete installation."
    Write-Host ""
    Write-Host "After installation:"
    Write-Host "  1. Open PowerShell"
    Write-Host "  2. Run: ollama pull neural-chat"
    Write-Host "  3. Run: ollama serve"
    
} catch {
    Write-Host "Error downloading: $_"
    Write-Host ""
    Write-Host "Manual installation:"
    Write-Host "1. Visit: https://ollama.ai/download"
    Write-Host "2. Download Ollama for Windows"
    Write-Host "3. Run the installer"
}
