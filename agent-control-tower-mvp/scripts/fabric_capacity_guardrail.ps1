param(
    [Parameter(Mandatory = $true)]
    [string]$SubscriptionId,

    [Parameter(Mandatory = $true)]
    [string]$ResourceGroupName,

    [Parameter(Mandatory = $true)]
    [string]$CapacityName,

    [switch]$OverrideNonF2,

    [ValidateSet("Check", "Suspend", "Resume")]
    [string]$Action = "Check"
)

$ErrorActionPreference = "Stop"

Write-Host "Fabric capacity guardrail check"
Write-Host "Subscription: $SubscriptionId"
Write-Host "Resource group: $ResourceGroupName"
Write-Host "Capacity: $CapacityName"
Write-Host "Requested action: $Action"

if (-not (Get-Module -ListAvailable -Name Az.Resources)) {
    Write-Error "Az.Resources is not installed. Install the Az PowerShell modules before running this template."
}

Set-AzContext -SubscriptionId $SubscriptionId | Out-Null

$resourceId = "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroupName/providers/Microsoft.Fabric/capacities/$CapacityName"
$capacity = Get-AzResource -ResourceId $resourceId

if (-not $capacity) {
    Write-Error "Fabric capacity was not found: $resourceId"
}

$skuName = $capacity.Sku.Name
$capacityState = $capacity.Properties.state
if (-not $capacityState) {
    $capacityState = $capacity.Properties.provisioningState
}

Write-Host "Capacity SKU: $skuName"
Write-Host "Capacity status: $capacityState"

if ($skuName -ne "F2" -and -not $OverrideNonF2) {
    Write-Error "Refusing to continue because capacity SKU is '$skuName', not 'F2'. Re-run with -OverrideNonF2 only if this is intentional."
}

if ($skuName -ne "F2" -and $OverrideNonF2) {
    Write-Warning "OverrideNonF2 was supplied. Continuing despite SKU '$skuName'."
}

switch ($Action) {
    "Check" {
        Write-Host "Check complete. No suspend or resume command was executed."
    }
    "Suspend" {
        Write-Warning "Suspend was explicitly requested."
        Write-Host "Placeholder only. Review Azure RBAC permissions and use the appropriate Azure management command or REST call."
        Write-Host "Example placeholder:"
        Write-Host "  Invoke-AzRestMethod -Method Post -Path '$resourceId/suspend?api-version=<api-version>'"
    }
    "Resume" {
        Write-Warning "Resume was explicitly requested."
        Write-Host "Placeholder only. Review Azure RBAC permissions and use the appropriate Azure management command or REST call."
        Write-Host "Example placeholder:"
        Write-Host "  Invoke-AzRestMethod -Method Post -Path '$resourceId/resume?api-version=<api-version>'"
    }
}
