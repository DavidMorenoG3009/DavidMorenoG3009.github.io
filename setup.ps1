# Configuración e Instalación Automatizada para Voice Keyboard Offline
$ErrorActionPreference = "Stop"

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " Instalador - Teclado de Voz Universal (Offline) " -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan

# 1. Comprobar que Python esté instalado
$pythonPath = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $pythonPath) {
    Write-Host "[!] Python no está instalado o no está en el PATH de Windows." -ForegroundColor Red
    Write-Host "Por favor, descarga Python desde la tienda de Windows o python.org y asegúrate de marcar 'Add to PATH'." -ForegroundColor Yellow
    exit 1
} else {
    Write-Host "[*] Python detectado en: $pythonPath" -ForegroundColor Green
}

# 2. Configurar entorno virtual
$venvDir = ".venv"
if (-not (Test-Path $venvDir)) {
    Write-Host "[*] Creando entorno virtual local ($venvDir) aislador..." -ForegroundColor Yellow
    python -m venv $venvDir
} else {
    Write-Host "[*] Entorno virtual ya existe. Continuando..." -ForegroundColor Green
}

# 3. Activar e Instalar librerías
Write-Host "[*] Instalando dependencias (Vosk, SoundDevice, Keyboard, PyAutoGUI)..." -ForegroundColor Yellow

$pipPath = ".\$venvDir\Scripts\pip.exe"
& $pipPath install --upgrade pip
& $pipPath install -r requirements.txt

# 4. Configurar un acceso directo o archivo BAT para lanzamiento rápido
$runnerBat = "start_voice_keyboard.bat"
$batContent = "@echo off`nTITLE Teclado de Voz Universal`n.\`$venvDir\Scripts\python.exe voice_keyboard.py`npause"
Set-Content -Path $runnerBat -Value $batContent
Write-Host "[*] Archivo '$runnerBat' creado para inicio rápido." -ForegroundColor Green

Write-Host "=============================================" -ForegroundColor Cyan
Write-Host " ¡Instalación Completada con Éxito! " -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "-> Para ejecutar el programa desde aquí en adelante simplemente:"
Write-Host "   Haz doble clic sobre el archivo '$runnerBat'"
Write-Host "   O bien ejecuta '.\$runnerBat' en esta consola."
Write-Host "-> Recuerda que la primera vez que la aplicación se ejecute, descargará el modelo de idioma español (~40MB)" -ForegroundColor Yellow
Write-Host "   y se descomprimirá solo." -ForegroundColor Yellow
