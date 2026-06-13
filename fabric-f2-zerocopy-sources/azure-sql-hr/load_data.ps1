<#
.SYNOPSIS
    Load the messy ERP HR dataset into the azure-sql-hr Azure SQL Database.

.DESCRIPTION
    Runs sql/schema.sql via sqlcmd to (re)create the CostCenters, Employees,
    Timesheets, and PayRuns tables, then bulk-loads each output/*.csv via bcp
    (ordinal load, skipping the CSV header row).

    Run generate_hr_data.py first to produce the CSVs, and provision_sql_db.ps1
    to provision the database. Safe to re-run: schema.sql drops and recreates
    each table before reloading.
#>

param(
    [string]$ResourceGroup = "rg-fabric-sandbox",
    [string]$ServerName = "sql-fabric-hr-demo",
    [string]$DatabaseName = "hr-erp",
    [string]$AdminUser = "hradmin",
    [string]$AdminPassword = ""
)

# Refresh PATH in case az/sqlcmd/bcp were installed after this shell started
$machinePath = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
$userPath = [System.Environment]::GetEnvironmentVariable("Path", "User")
$env:Path = "$machinePath;$userPath"

$root = $PSScriptRoot
$schemaPath = Join-Path $root "sql\schema.sql"
$outputDir = Join-Path $root "output"

if (-not (Test-Path $schemaPath)) {
    Write-Host "ERROR: $schemaPath not found. Run generate_hr_data.py first." -ForegroundColor Red
    exit 1
}

Write-Host "== Azure account ==" -ForegroundColor Cyan
$account = az account show -o json 2>$null | ConvertFrom-Json
if (-not $account) {
    Write-Host "ERROR: not logged in. Run scripts\preflight.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "`n== SQL server ==" -ForegroundColor Cyan
$server = az sql server show --name $ServerName --resource-group $ResourceGroup -o json 2>$null | ConvertFrom-Json
if (-not $server) {
    Write-Host "ERROR: server '$ServerName' not found in $ResourceGroup. Run provision_sql_db.ps1 first." -ForegroundColor Red
    exit 1
}
$fqdn = $server.fullyQualifiedDomainName
Write-Host "Server: $fqdn"

$existingDb = az sql db show --resource-group $ResourceGroup --server $ServerName --name $DatabaseName -o json 2>$null | ConvertFrom-Json
if (-not $existingDb) {
    Write-Host "ERROR: database '$DatabaseName' not found on $ServerName. Run provision_sql_db.ps1 first." -ForegroundColor Red
    exit 1
}
Write-Host "Database: $DatabaseName ($($existingDb.requestedServiceObjectiveName), auto-pause $($existingDb.autoPauseDelay) min)"

if ($AdminPassword) {
    $plainPwd = $AdminPassword
} else {
    $securePwd = Read-Host "Admin password for '$AdminUser' (input hidden, not stored)" -AsSecureString
    $plainPwd = [System.Net.NetworkCredential]::new("", $securePwd).Password
}

Write-Host "`n== Applying schema ==" -ForegroundColor Cyan
sqlcmd -S $fqdn -d $DatabaseName -U $AdminUser -P $plainPwd -i $schemaPath
if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: sqlcmd failed to apply schema.sql" -ForegroundColor Red
    exit 1
}
Write-Host "Schema applied" -ForegroundColor Green

$tables = @("CostCenters", "Employees", "Timesheets", "PayRuns")
$errorDir = Join-Path $root "load_errors"
New-Item -ItemType Directory -Force -Path $errorDir | Out-Null

Write-Host "`n== Bulk loading data (bcp) ==" -ForegroundColor Cyan
foreach ($table in $tables) {
    $csvPath = Join-Path $outputDir "$table.csv"
    if (-not (Test-Path $csvPath)) {
        Write-Host "WARNING: $csvPath not found - skipping $table" -ForegroundColor Yellow
        continue
    }

    $errPath = Join-Path $errorDir "$table.err"
    bcp "dbo.$table" in $csvPath -S $fqdn -d $DatabaseName -U $AdminUser -P $plainPwd -c -C 65001 "-t," -F 2 -e $errPath

    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: bcp load failed for $table - see $errPath" -ForegroundColor Red
    } else {
        Write-Host "Loaded $table" -ForegroundColor Green
        if ((Test-Path $errPath) -and (Get-Item $errPath).Length -gt 0) {
            Write-Host "  WARNING: some rows were rejected - see $errPath" -ForegroundColor Yellow
        }
    }
}

Write-Host "`n== Row counts ==" -ForegroundColor Cyan
$countQuery = ($tables | ForEach-Object { "SELECT '$_' AS TableName, COUNT(*) AS RowCnt FROM dbo.$_" }) -join " UNION ALL "
sqlcmd -S $fqdn -d $DatabaseName -U $AdminUser -P $plainPwd -Q $countQuery

Write-Host "`nLoad complete." -ForegroundColor Green
Write-Host "Next: update COST_TRACKER.md and follow docs\azure-sql-hr-checklist.md for Fabric Mirroring."
