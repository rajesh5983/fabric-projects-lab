<#
.SYNOPSIS
    Upload the generated IronWatch landing-zone sample files to the
    "ironwatch-landing" ADLS Gen2 container.

.DESCRIPTION
    Uploads all files from .\output\ (produced by generate_ironwatch_data.py)
    to the target container using Azure AD auth (--auth-mode login), so no
    storage account keys are needed.

    Run provision_storage.ps1 first to create the storage account and
    container, and generate_ironwatch_data.py to produce the output files.
#>

param(
    [string]$ResourceGroup = "rg-fabric-sandbox",
    [string]$StorageAccountName = "fabricf2landingsa",
    [string]$ContainerName = "ironwatch-landing"
)

# Refresh PATH in case az was installed after this shell started
$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

$root = $PSScriptRoot
$outputDir = Join-Path $root "output"

if (-not (Test-Path $outputDir)) {
    Write-Host "ERROR: $outputDir not found. Run generate_ironwatch_data.py first." -ForegroundColor Red
    exit 1
}

Write-Host "== Azure account ==" -ForegroundColor Cyan
$account = az account show -o json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "ERROR: not logged in. Run scripts\preflight.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "`n== Storage account ==" -ForegroundColor Cyan
$storage = az storage account show --name $StorageAccountName --resource-group $ResourceGroup -o json 2>$null | ConvertFrom-Json
if (-not $storage) {
    Write-Host "ERROR: storage account '$StorageAccountName' not found in $ResourceGroup. Run provision_storage.ps1 first." -ForegroundColor Red
    exit 1
}
Write-Host "Account: $StorageAccountName (sku $($storage.sku.name))"

$container = az storage container show --account-name $StorageAccountName --name $ContainerName --auth-mode login -o json 2>$null | ConvertFrom-Json
if (-not $container) {
    Write-Host "ERROR: container '$ContainerName' not found on $StorageAccountName. Run provision_storage.ps1 first." -ForegroundColor Red
    exit 1
}
Write-Host "Container: $ContainerName"

$files = Get-ChildItem -Path $outputDir -File
if ($files.Count -eq 0) {
    Write-Host "ERROR: $outputDir is empty. Run generate_ironwatch_data.py first." -ForegroundColor Red
    exit 1
}

Write-Host "`n== Uploading files ==" -ForegroundColor Cyan
foreach ($file in $files) {
    $sizeKb = [math]::Round($file.Length / 1KB, 1)
    Write-Host "  $($file.Name) ($sizeKb KB)"
}

az storage blob upload-batch `
    --account-name $StorageAccountName `
    --destination $ContainerName `
    --source $outputDir `
    --auth-mode login `
    --overwrite `
    -o none

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: az storage blob upload-batch failed." -ForegroundColor Red
    exit 1
}

Write-Host "`n== Verifying uploaded blobs ==" -ForegroundColor Cyan
az storage blob list `
    --account-name $StorageAccountName `
    --container-name $ContainerName `
    --auth-mode login `
    --query "[].{name:name, sizeBytes:properties.contentLength}" `
    -o table

Write-Host "`nUpload complete." -ForegroundColor Green
Write-Host "Next: update COST_TRACKER.md and follow docs\landing-zone-checklist.md to create the OneLake Shortcut."
