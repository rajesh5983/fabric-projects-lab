<#
.SYNOPSIS
    Preflight checks for fabric-f2-zerocopy-sources: Azure CLI auth, subscription,
    resource groups, Budget-2026 status, Fabric capacity, and local Python venv.

.DESCRIPTION
    Run this before any provisioning step, and re-run any time as a sanity check.
    It is idempotent — login, subscription switch, and resource group creation
    are all safe to repeat.
#>

$DemoResourceGroup = "rg-fabric-zerocopy-demo"
$SharedInfraResourceGroup = "rg-shared-infra"
$DemoLocation = "australiaeast"

# Refresh PATH in case az was installed after this shell started
$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

Write-Host "== Azure CLI ==" -ForegroundColor Cyan
$verInfo = az version -o json | ConvertFrom-Json
Write-Host "azure-cli $($verInfo.'azure-cli')"

Write-Host "`n== Azure login ==" -ForegroundColor Cyan
$account = az account show -o json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "Not logged in - starting device code login..." -ForegroundColor Yellow
    az login --use-device-code -o none
    $account = az account show -o json 2>$null | ConvertFrom-Json
}
if (-not $account) {
    Write-Host "ERROR: az login failed - aborting preflight." -ForegroundColor Red
    exit 1
}
Write-Host "Logged in as $($account.user.name) | Subscription: $($account.name)"

Write-Host "`n== Subscription ==" -ForegroundColor Cyan
if ($account.name -ne "ModernAnalyticsLab") {
    az account set --subscription "ModernAnalyticsLab"
    $account = az account show -o json | ConvertFrom-Json
    Write-Host "Switched subscription to ModernAnalyticsLab"
} else {
    Write-Host "Subscription already set to ModernAnalyticsLab"
}

Write-Host "`n== Resource groups ==" -ForegroundColor Cyan
$groups = az group list -o json | ConvertFrom-Json
foreach ($g in $groups) {
    Write-Host " - $($g.name) ($($g.location))"
}

$sharedInfra = $groups | Where-Object { $_.name -eq $SharedInfraResourceGroup }
if ($sharedInfra) {
    Write-Host "$SharedInfraResourceGroup exists ($($sharedInfra.location))" -ForegroundColor Green
} else {
    Write-Host "NOTE: $SharedInfraResourceGroup not found - shared capacity pause/resume automation may live elsewhere" -ForegroundColor Yellow
}

$demoRg = $groups | Where-Object { $_.name -eq $DemoResourceGroup }
if ($demoRg) {
    Write-Host "$DemoResourceGroup exists ($($demoRg.location))" -ForegroundColor Green
} else {
    Write-Host "$DemoResourceGroup not found - creating in $DemoLocation..." -ForegroundColor Yellow
    az group create --name $DemoResourceGroup --location $DemoLocation -o none
    Write-Host "Created $DemoResourceGroup ($DemoLocation)" -ForegroundColor Green
}

Write-Host "`n== Budget-2026 ==" -ForegroundColor Cyan
$budget = try { az consumption budget show --budget-name Budget-2026 -o json 2>$null | ConvertFrom-Json } catch { $null }
if ($budget) {
    $spend = [double]$budget.currentSpend.amount
    $amount = [double]$budget.amount
    $pct = [math]::Round(($spend / $amount) * 100, 1)
    Write-Host "Spend: $spend / $amount $($budget.currentSpend.unit) ($pct% of monthly budget)"
    if ($budget.notifications) {
        foreach ($key in $budget.notifications.PSObject.Properties.Name) {
            $n = $budget.notifications.$key
            $hit = $pct -ge $n.threshold
            $status = if ($hit) { "ALERT THRESHOLD CROSSED" } else { "ok" }
            $color = if ($hit) { "Red" } else { "DarkGray" }
            Write-Host "  $key : $($n.threshold)% threshold, enabled=$($n.enabled) -> $status" -ForegroundColor $color
        }
    }
} else {
    Write-Host "WARNING: Could not retrieve Budget-2026 status (check Cost Management Reader access)" -ForegroundColor Yellow
}

Write-Host "`n== Fabric capacity (rg-fabric-sandbox) ==" -ForegroundColor Cyan
$capacity = az resource list --resource-group rg-fabric-sandbox `
    --query "[?type=='Microsoft.Fabric/capacities']" -o json | ConvertFrom-Json
if ($capacity) {
    Write-Host "Found: $($capacity[0].name) ($($capacity[0].location))" -ForegroundColor Green
} else {
    Write-Host "WARNING: No Fabric capacity found in rg-fabric-sandbox" -ForegroundColor Yellow
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

Write-Host "`n========================================" -ForegroundColor Magenta
Write-Host "  BEFORE CREATING ANY RESOURCE:" -ForegroundColor Magenta
Write-Host "  [ ] Confirm it's a serverless / free-tier SKU" -ForegroundColor Magenta
Write-Host "  [ ] Confirm auto-pause / auto-shutdown is configured" -ForegroundColor Magenta
Write-Host "  [ ] Place it in $DemoResourceGroup and record it in COST_TRACKER.md" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

Write-Host "`nPreflight complete." -ForegroundColor Green
