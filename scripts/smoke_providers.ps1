param(
  [string]$BackendUrl = "http://127.0.0.1:8000"
)
$ErrorActionPreference = "Stop"
$providers = @("openai", "deepseek", "qwen")
foreach ($provider in $providers) {
  Write-Host "Testing $provider configuration..."
  $settings = Invoke-RestMethod -Uri "$BackendUrl/api/settings"
  $item = $settings.providers | Where-Object { $_.provider -eq $provider }
  if (-not $item.api_key_configured) {
    Write-Host "SKIP: $provider API key is not configured"
    continue
  }
  $body = @{ model=$item.model; base_url=$item.base_url; timeout_seconds=60 } | ConvertTo-Json
  Invoke-RestMethod -Method Post -Uri "$BackendUrl/api/settings/providers/$provider/test" -ContentType "application/json" -Body $body
  Write-Host "PASS: $provider"
}
