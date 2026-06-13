<#
.SYNOPSIS
    Provision an Azure SQL Database (General Purpose, Serverless, Gen5, 1 vCore,
    60-min auto-pause) for the azure-sql-hr Fabric Mirroring demo.

.DESCRIPTION
    Creates the logical SQL server (if it doesn't exist), opens firewall rules
    for Azure services and this machine's public IP, then creates the database
    in rg-fabric-sandbox.

    GUARDRAIL: before 'az sql db create' runs, the script verifies ComputeModel
    is 'Serverless' and AutoPauseDelay > 0, prints the resolved configuration
    and an estimated cost, and asks for confirmation (skip with -Yes).

    Run scripts\preflight.ps1 first to confirm az login, subscription, and that
    rg-fabric-sandbox exists. Safe to re-run: server/firewall/database creation
    are all skipped if they already exist.
#>

param(
    [string]$ResourceGroup = "rg-fabric-sandbox",
    [string]$Location = "australiaeast",
    [string]$ServerName = "sql-fabric-hr-demo",
    [string]$DatabaseName = "hr-erp",
    [string]$AdminUser = "hradmin",
    [string]$AdminPassword = "",
    [string]$Edition = "GeneralPurpose",
    [string]$Family = "Gen5",
    [int]$Capacity = 1,
    [string]$ComputeModel = "Serverless",
    [double]$MinCapacity = 0.5,
    [int]$AutoPauseDelay = 60,
    [switch]$Yes
)

# Refresh PATH in case az was installed after this shell started
$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

Write-Host "== Azure account ==" -ForegroundColor Cyan
$account = az account show -o json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "ERROR: not logged in. Run scripts\preflight.ps1 first." -ForegroundColor Red
    exit 1
}
if ($account.name -ne "ModernAnalyticsLab") {
    Write-Host "ERROR: wrong subscription ('$($account.name)'). Run scripts\preflight.ps1 first." -ForegroundColor Red
    exit 1
}
Write-Host "Subscription: $($account.name)"

Write-Host "`n== Resource group ==" -ForegroundColor Cyan
$rg = az group show --name $ResourceGroup -o json 2>$null | ConvertFrom-Json
if (-not $rg) {
    Write-Host "ERROR: resource group '$ResourceGroup' not found. Run scripts\preflight.ps1 first." -ForegroundColor Red
    exit 1
}
Write-Host "$ResourceGroup exists ($($rg.location))" -ForegroundColor Green

Write-Host "`n== SQL logical server ==" -ForegroundColor Cyan
$server = az sql server show --name $ServerName --resource-group $ResourceGroup -o json 2>$null | ConvertFrom-Json
if ($server) {
    Write-Host "$ServerName already exists ($($server.fullyQualifiedDomainName))" -ForegroundColor Green
} else {
    Write-Host "$ServerName not found - will create it." -ForegroundColor Yellow
    if ($AdminPassword) {
        $plainPwd = $AdminPassword
    } else {
        Write-Host "Choose an admin password for SQL login '$AdminUser' (8-128 chars, 3 of: upper/lower/digit/symbol)."
        Write-Host "Avoid the characters & | < > ^ % and double-quotes - they can be mangled when passed through to az.cmd on Windows." -ForegroundColor Yellow
        $securePwd = Read-Host "Admin password (input hidden, not stored)" -AsSecureString
        $plainPwd = [System.Net.NetworkCredential]::new("", $securePwd).Password
    }

    az sql server create `
        --name $ServerName `
        --resource-group $ResourceGroup `
        --location $Location `
        --admin-user $AdminUser `
        --admin-password $plainPwd `
        -o none
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: az sql server create failed (server name must be globally unique - try -ServerName <something-unique>)." -ForegroundColor Red
        exit 1
    }
    $server = az sql server show --name $ServerName --resource-group $ResourceGroup -o json | ConvertFrom-Json
    Write-Host "Created $ServerName ($($server.fullyQualifiedDomainName))" -ForegroundColor Green
}

Write-Host "`n== Firewall rules ==" -ForegroundColor Cyan
$existingRules = az sql server firewall-rule list --resource-group $ResourceGroup --server $ServerName -o json | ConvertFrom-Json

if (-not ($existingRules | Where-Object { $_.name -eq "AllowAzureServices" })) {
    az sql server firewall-rule create --resource-group $ResourceGroup --server $ServerName `
        --name AllowAzureServices --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0 -o none
    Write-Host "Added AllowAzureServices firewall rule" -ForegroundColor Green
} else {
    Write-Host "AllowAzureServices firewall rule already present" -ForegroundColor Green
}

try {
    $myIp = (Invoke-RestMethod -Uri "https://api.ipify.org" -TimeoutSec 10).Trim()
    $ruleName = "AllowClient-$($myIp.Replace('.', '-'))"
    if (-not ($existingRules | Where-Object { $_.name -eq $ruleName })) {
        az sql server firewall-rule create --resource-group $ResourceGroup --server $ServerName `
            --name $ruleName --start-ip-address $myIp --end-ip-address $myIp -o none
        Write-Host "Added firewall rule for this machine's IP ($myIp)" -ForegroundColor Green
    } else {
        Write-Host "Firewall rule for this machine's IP ($myIp) already present" -ForegroundColor Green
    }
} catch {
    Write-Host "WARNING: could not detect this machine's public IP - add a firewall rule manually before running load_data.ps1" -ForegroundColor Yellow
}

Write-Host "`n== Database already exists? ==" -ForegroundColor Cyan
$existingDb = az sql db show --resource-group $ResourceGroup --server $ServerName --name $DatabaseName -o json 2>$null | ConvertFrom-Json
if ($existingDb) {
    Write-Host "$DatabaseName already exists on $ServerName - nothing to create." -ForegroundColor Green
    Write-Host "Compute model: $($existingDb.requestedServiceObjectiveName) | Auto-pause: $($existingDb.autoPauseDelay) min"
    exit 0
}

Write-Host "`n== Database configuration ==" -ForegroundColor Cyan

# GUARDRAIL: refuse to proceed unless this is serverless with auto-pause enabled.
if ($ComputeModel -ne "Serverless" -or $AutoPauseDelay -le 0) {
    Write-Host "ERROR: guardrail failed - ComputeModel must be 'Serverless' and AutoPauseDelay > 0 (got ComputeModel='$ComputeModel', AutoPauseDelay=$AutoPauseDelay)." -ForegroundColor Red
    exit 1
}

Write-Host "Server:         $ServerName ($($server.fullyQualifiedDomainName))"
Write-Host "Database:       $DatabaseName"
Write-Host "Resource group: $ResourceGroup ($Location)"
Write-Host "Edition:        $Edition"
Write-Host "Family:         $Family"
Write-Host "Capacity:       $Capacity vCore (max)"
Write-Host "Compute model:  $ComputeModel" -ForegroundColor Green
Write-Host "Min capacity:   $MinCapacity vCore (when active)"
Write-Host "Auto-pause:     $AutoPauseDelay minutes" -ForegroundColor Green
Write-Host "Guardrail check passed: serverless with auto-pause enabled." -ForegroundColor Green

Write-Host "`n== Estimated cost (rough - verify with Azure Pricing Calculator) ==" -ForegroundColor Cyan
Write-Host "Compute: ~AUD `$0.20-`$0.80 per vCore-hour while online ($MinCapacity-$Capacity vCore), `$0 while auto-paused"
Write-Host "Storage: ~32 GB allocated x ~AUD `$0.17/GB/month = ~AUD `$5/month (billed even while paused)"
Write-Host "For light/sporadic demo use with a $AutoPauseDelay-minute auto-pause, expect roughly AUD `$5-15/month total."
Write-Host "Counts against Budget-2026 (`$50 AUD/month) - record this resource in COST_TRACKER.md." -ForegroundColor Yellow

if (-not $Yes) {
    $confirm = Read-Host "`nProceed with 'az sql db create' for $DatabaseName on $ServerName? (y/N)"
    if ($confirm -notmatch '^[Yy]') {
        Write-Host "Aborted - no database created." -ForegroundColor Yellow
        exit 0
    }
}

Write-Host "`n== Creating database ==" -ForegroundColor Cyan
az sql db create `
    --resource-group $ResourceGroup `
    --server $ServerName `
    --name $DatabaseName `
    --edition $Edition `
    --family $Family `
    --capacity $Capacity `
    --compute-model $ComputeModel `
    --min-capacity $MinCapacity `
    --auto-pause-delay $AutoPauseDelay `
    -o none

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: az sql db create failed." -ForegroundColor Red
    exit 1
}

Write-Host "`nCreated $DatabaseName on $($server.fullyQualifiedDomainName)" -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. .\load_data.ps1 -ServerName $ServerName -DatabaseName $DatabaseName -AdminUser $AdminUser"
Write-Host "  2. Update COST_TRACKER.md with this resource"
Write-Host "  3. Follow docs\azure-sql-hr-checklist.md to enable Fabric Mirroring"
