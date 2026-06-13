<#
.SYNOPSIS
    Provision an ADLS Gen2 storage account (Standard LRS, StorageV2 +
    hierarchical namespace) for the landing-zone OneLake Shortcut demo.

.DESCRIPTION
    Creates the storage account (if it doesn't exist) in rg-fabric-sandbox,
    then creates a single container "ironwatch-landing" inside it.

    GUARDRAIL: before 'az storage account create' runs, the script verifies
    Sku is 'Standard_LRS', prints the resolved configuration and pricing
    tier, and asks for confirmation (skip with -Yes).

    Run scripts\preflight.ps1 first to confirm az login, subscription, and
    that rg-fabric-sandbox exists. Safe to re-run: account/container creation
    are skipped if they already exist.
#>

param(
    [string]$ResourceGroup = "rg-fabric-sandbox",
    [string]$Location = "australiaeast",
    [string]$StorageAccountName = "fabricf2landingsa",
    [string]$ContainerName = "ironwatch-landing",
    [string]$Sku = "Standard_LRS",
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

Write-Host "`n== Storage account ==" -ForegroundColor Cyan
$storage = az storage account show --name $StorageAccountName --resource-group $ResourceGroup -o json 2>$null | ConvertFrom-Json
if ($storage) {
    Write-Host "$StorageAccountName already exists (sku $($storage.sku.name), hns $($storage.isHnsEnabled))" -ForegroundColor Green
} else {
    Write-Host "$StorageAccountName not found - will create it." -ForegroundColor Yellow

    # GUARDRAIL: refuse to proceed unless this is the lowest-cost Standard LRS tier.
    if ($Sku -ne "Standard_LRS") {
        Write-Host "ERROR: guardrail failed - Sku must be 'Standard_LRS' (got '$Sku')." -ForegroundColor Red
        exit 1
    }

    Write-Host "`n== Storage account configuration ==" -ForegroundColor Cyan
    Write-Host "Name:           $StorageAccountName"
    Write-Host "Resource group: $ResourceGroup ($Location)"
    Write-Host "Kind:           StorageV2 (ADLS Gen2, hierarchical namespace enabled)"
    Write-Host "Pricing tier:   $Sku (lowest-cost redundancy tier)" -ForegroundColor Green
    Write-Host "Access tier:    Hot"
    Write-Host "Container:      $ContainerName"
    Write-Host "Guardrail check passed: Standard_LRS confirmed." -ForegroundColor Green

    Write-Host "`n== Estimated cost (rough - verify with Azure Pricing Calculator) ==" -ForegroundColor Cyan
    Write-Host "Storage: Standard LRS Hot tier ~AUD `$0.03/GB/month. This demo's synthetic"
    Write-Host "dataset is only a few MB, so storage cost is well under AUD `$0.10/month."
    Write-Host "Transactions: negligible at this scale (a handful of uploads/Shortcut reads)."
    Write-Host "Counts against Budget-2026 (`$50 AUD/month) - record this resource in COST_TRACKER.md." -ForegroundColor Yellow

    if (-not $Yes) {
        $confirm = Read-Host "`nProceed with 'az storage account create' for $StorageAccountName ($Sku)? (y/N)"
        if ($confirm -notmatch '^[Yy]') {
            Write-Host "Aborted - no storage account created." -ForegroundColor Yellow
            exit 0
        }
    }

    Write-Host "`n== Creating storage account ==" -ForegroundColor Cyan
    az storage account create `
        --name $StorageAccountName `
        --resource-group $ResourceGroup `
        --location $Location `
        --sku $Sku `
        --kind StorageV2 `
        --enable-hierarchical-namespace true `
        --access-tier Hot `
        --min-tls-version TLS1_2 `
        -o none

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: az storage account create failed (account name must be globally unique - try -StorageAccountName <something-unique>)." -ForegroundColor Red
        exit 1
    }
    $storage = az storage account show --name $StorageAccountName --resource-group $ResourceGroup -o json | ConvertFrom-Json
    Write-Host "Created $StorageAccountName (sku $($storage.sku.name), hns $($storage.isHnsEnabled))" -ForegroundColor Green
}

Write-Host "`n== Container ==" -ForegroundColor Cyan
$existingContainer = az storage container show --account-name $StorageAccountName --name $ContainerName --auth-mode login -o json 2>$null | ConvertFrom-Json
if ($existingContainer) {
    Write-Host "Container '$ContainerName' already exists" -ForegroundColor Green
} else {
    az storage container create --account-name $StorageAccountName --name $ContainerName --auth-mode login -o none
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: failed to create container '$ContainerName'." -ForegroundColor Red
        exit 1
    }
    Write-Host "Created container '$ContainerName'" -ForegroundColor Green
}

Write-Host "`nProvisioning complete." -ForegroundColor Green
Write-Host "Next steps:"
Write-Host "  1. .venv\Scripts\python.exe landing-zone\generate_ironwatch_data.py"
Write-Host "  2. .\landing-zone\upload_to_landing.ps1 -StorageAccountName $StorageAccountName -ContainerName $ContainerName"
Write-Host "  3. Update COST_TRACKER.md with this resource"
Write-Host "  4. Follow docs\landing-zone-checklist.md to create the OneLake Shortcut"
