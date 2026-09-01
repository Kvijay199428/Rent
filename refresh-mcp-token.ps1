# refresh-mcp-token.ps1
# Fetches the current Cloudflare OAuth token and refreshes CLOUDFLARE_MCP_TOKEN
# used as the shared Authorization bearer for all Cloudflare MCP servers.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\refresh-mcp-token.ps1
$ErrorActionPreference = 'Stop'

if (-not (Get-Command npx -ErrorAction SilentlyContinue)) {
    Write-Host 'npx not found. Install Node.js first.' -ForegroundColor Red
    exit 1
}

Write-Host 'Fetching Cloudflare auth token...' -ForegroundColor Cyan
$token = (& npx wrangler auth token 2>$null) | Select-Object -Last 1
if (-not $token -or $token.Length -lt 20) {
    Write-Host 'No valid token. Log in first: npx wrangler login' -ForegroundColor Red
    exit 1
}

if ($env:CLOUDFLARE_MCP_TOKEN -eq $token) {
    Write-Host 'Token unchanged. Nothing to do.' -ForegroundColor Yellow
} else {
    [Environment]::SetEnvironmentVariable('CLOUDFLARE_MCP_TOKEN', $token, 'User')
    $env:CLOUDFLARE_MCP_TOKEN = $token
    Write-Host "Token refreshed (length $($token.Length))." -ForegroundColor Green
}

Write-Host 'Verifying against mcp.cloudflare.com...' -ForegroundColor Cyan
$body = '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"token-refresh","version":"1.0"}}}'
$bodyFile = Join-Path $env:TEMP 'mcp_refresh_body.json'
Set-Content -Path $bodyFile -Value $body -NoNewline
$code = curl.exe -s -o NUL -w "%{http_code}" -X POST "https://mcp.cloudflare.com/mcp" -H "Content-Type: application/json" -H "Accept: application/json, text/event-stream" -H "Authorization: Bearer $token" --data "@$bodyFile"
Remove-Item -Path $bodyFile -ErrorAction SilentlyContinue

if ($code -eq '200') {
    Write-Host 'Token verified (HTTP 200). Restart opencode to pick it up.' -ForegroundColor Green
} else {
    Write-Host "Warning: verification returned HTTP $code. Token may be rejected or expired." -ForegroundColor Yellow
}