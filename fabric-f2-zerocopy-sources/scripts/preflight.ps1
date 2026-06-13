<#
.SYNOPSIS
    Preflight checks for fabric-f2-zerocopy-sources: Azure CLI auth, subscription,
    Fabric capacity, Budget-2026 status, and local Python venv.
#>

$ErrorActionPreference = "Stop"

# Refresh PATH in case az was installed after this shell started
$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

Write-Host "== Azure CLI ==" -ForegroundColor Cyan
az version -o tsv --query '"azure-cli"'

Write-Host "`n== Azure account ==" -ForegroundColor Cyan
$account = az account show -o json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in. Run: az login --use-device-code" -ForegroundColor Yellow
    exit 1
}
Write-Host "Logged in as $($account.user.name) | Subscription: $($account.name)"

if ($account.name -ne "ModernAnalyticsLab") {
    az account set --subscription "ModernAnalyticsLab"
    Write-Host "Switched subscription to ModernAnalyticsLab"
}

Write-Host "`n== Fabric capacity (rg-fabric-sandbox) ==" -ForegroundColor Cyan
$capacity = az resource list --resource-group rg-fabric-sandbox `
    --query "[?type=='Microsoft.Fabric/capacities']" -o json | ConvertFrom-Json
if ($capacity) {
    Write-Host "Found: $($capacity[0].name) ($($capacity[0].location))" -ForegroundColor Green
} else {
    Write-Host "WARNING: No Fabric capacity found in rg-fabric-sandbox" -ForegroundColor Yellow
}

Write-Host "`n== Budget-2026 ==" -ForegroundColor Cyan
$budget = az consumption budget show --budget-name Budget-2026 -o json 2>$null | ConvertFrom-Json
if ($budget) {
    Write-Host "Spend: $($budget.currentSpend.amount) / $($budget.amount) $($budget.currentSpend.unit) (monthly)"
} else {
    Write-Host "WARNING: Could not retrieve Budget-2026 status" -ForegroundColor Yellow
}

Write-Host "`n== Python virtual environment ==" -ForegroundColor Cyan
$venvPath = Join-Path $PSScriptRoot "..\.venv"
if (-not (Test-Path $venvPath)) {
    Write-Host "Creating .venv at $venvPath"
    python -m venv $venvPath
}
& "$venvPath\Scripts\python.exe" -m pip install --quiet --upgrade pip
& "$venvPath\Scripts\python.exe" -m pip install --quiet faker requests azure-eventhub
Write-Host "Python venv ready: faker, requests, azure-eventhub installed" -ForegroundColor Green

Write-Host "`nPreflight complete." -ForegroundColor Green
