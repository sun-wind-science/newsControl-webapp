param(
  [int]$BackendPort = 8000,
  [int]$FrontendPort = 3000
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

$env:BACKEND_HOSTPORT = "localhost:$BackendPort"
$env:SERVER_API_BASE_URL = "http://localhost:$BackendPort"

Write-Host "后端端口: $BackendPort"
Write-Host "前端端口: $FrontendPort"
Write-Host "前端代理: $env:SERVER_API_BASE_URL"

if (-not (Test-Path (Join-Path $backend ".venv\Scripts\python.exe"))) {
  Write-Host "创建后端虚拟环境..."
  Push-Location $backend
  python -m venv .venv
  .\.venv\Scripts\python.exe -m pip install -r requirements.txt
  Pop-Location
}

if (-not (Test-Path (Join-Path $frontend "node_modules"))) {
  Write-Host "安装前端依赖..."
  Push-Location $frontend
  npm install
  Pop-Location
}

Write-Host "启动后端..."
Start-Process -FilePath (Join-Path $backend ".venv\Scripts\python.exe") `
  -ArgumentList "-m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort" `
  -WorkingDirectory $backend `
  -WindowStyle Hidden

Start-Sleep -Seconds 2

Write-Host "启动前端..."
Start-Process -FilePath "npm.cmd" `
  -ArgumentList "run dev -- --port $FrontendPort" `
  -WorkingDirectory $frontend `
  -WindowStyle Hidden

Write-Host "打开 http://localhost:$FrontendPort"
