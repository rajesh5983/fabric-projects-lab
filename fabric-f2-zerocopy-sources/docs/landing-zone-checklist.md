# landing-zone → OneLake Shortcut: manual setup checklist

OneLake Shortcuts to ADLS Gen2 are created through the Fabric portal (no
CLI/API in this workflow). This checklist covers the manual steps after
`landing-zone/provision_storage.ps1` and `landing-zone/upload_to_landing.ps1`
have run successfully.

## 0. Prerequisites (should already be true)

- [ ] `fabricf2landingsa` exists in `rg-fabric-sandbox` (Standard_LRS,
      StorageV2, hierarchical namespace enabled) —
      `landing-zone/provision_storage.ps1`.
- [ ] Container `ironwatch-landing` contains 5 files, uploaded via
      `landing-zone/upload_to_landing.ps1`:
      `asset_master.csv`, `telemetry.parquet`, `fault_codes.json`,
      `service_history.csv`, `oil_samples.csv` (~386 KB total, 5 blobs).
- [ ] You have a Fabric workspace assigned to the `fabricf2sandbox` (F2)
      capacity in `rg-fabric-sandbox`, and at least Contributor role on it.
- [ ] You have a Lakehouse item in that workspace (create one if needed:
      **+ New item → Lakehouse**).

## 1. Record the baseline (before creating the Shortcut)

Storage metrics comparison only means something if you capture a "before"
snapshot. Run this now and keep the output:

```powershell
az storage blob list `
    --account-name fabricf2landingsa `
    --container-name ironwatch-landing `
    --auth-mode login `
    --query "[].{name:name, sizeBytes:properties.contentLength}" `
    -o table
```

Expected baseline (5 blobs, ~386 KB total):

| name | sizeBytes |
|---|---|
| asset_master.csv | 422 |
| fault_codes.json | 4247 |
| oil_samples.csv | 5216 |
| service_history.csv | 1329 |
| telemetry.parquet | 384392 |

Also note the storage account's **Used capacity** metric:

- [ ] Azure Portal → `fabricf2landingsa` → **Monitoring → Metrics** → Metric
      = "Used capacity" (or "Blob Capacity" for the blob/account scope).
      Record the current value (should be ~0.4 MB).

## 2. Grant Fabric access to the storage account

Pick **one** of:

- **Option A — Entra ID / organizational account (recommended):** assign
  yourself (or the workspace's identity) the `Storage Blob Data Reader` role
  on the storage account:

  ```powershell
  $me = az ad signed-in-user show --query id -o tsv
  az role assignment create `
      --assignee $me `
      --role "Storage Blob Data Reader" `
      --scope "/subscriptions/e82368b1-cb9b-4d92-826c-5b1e5e215d6d/resourceGroups/rg-fabric-sandbox/providers/Microsoft.Storage/storageAccounts/fabricf2landingsa"
  ```

  Then in Fabric, choose **Organizational account** as the connection
  credential and sign in with the same Entra identity.

- **Option B — Account key (quick demo only):** in the Fabric connection
  dialog, choose **Account key** and paste a key from:

  ```powershell
  az storage account keys list --account-name fabricf2landingsa --resource-group rg-fabric-sandbox -o table
  ```

  Account keys grant full access to the storage account — prefer Option A
  outside of throwaway demos.

## 3. Create the Shortcut

- [ ] Open the Lakehouse in your Fabric workspace.
- [ ] In the **Explorer** pane, right-click **Files** (or a subfolder) →
      **New shortcut**.
- [ ] Choose **Azure Data Lake Storage Gen2**.
- [ ] Enter the connection details:
  - **URL**: `https://fabricf2landingsa.dfs.core.windows.net/`
  - **Connection**: create new, using the credential from step 2.
- [ ] On the next screen, browse into the `ironwatch-landing` container and
      select it (or a subfolder) as the shortcut target.
- [ ] Name the shortcut, e.g. `ironwatch-landing`, and click **Create**.

## 4. Confirm the Shortcut works (zero-copy read)

- [ ] In the Lakehouse **Files** view, expand the new `ironwatch-landing`
      shortcut — you should see all 5 files (`asset_master.csv`,
      `telemetry.parquet`, `fault_codes.json`, `service_history.csv`,
      `oil_samples.csv`) with sizes matching the baseline in step 1.
- [ ] Open a notebook (or use **Load to Tables**) and read one of the files
      through the shortcut path, e.g.:

  ```python
  df = spark.read.parquet("Files/ironwatch-landing/telemetry.parquet")
  df.count()  # expect 28800
  ```

## 5. Verify no data was duplicated (storage metrics comparison)

The whole point of a Shortcut is that Fabric reads directly from
`fabricf2landingsa` — OneLake doesn't get its own copy of the bytes. Confirm
this two ways:

- [ ] **Source storage account unchanged.** Re-run the same `az storage blob
      list` command from step 1. The blob count (5) and `sizeBytes` values
      must be **identical** to the baseline — reading through the shortcut
      does not write anything back to `ironwatch-landing`. Also re-check the
      "Used capacity" metric in the portal — it should be unchanged
      (still ~0.4 MB), even after browsing/querying via the shortcut.

- [ ] **OneLake storage unchanged.** Open the **Fabric Capacity Metrics**
      app (or Workspace settings → **OneLake storage** / the Lakehouse's
      **Settings → Storage** if available) and check the OneLake storage
      consumption for this workspace/Lakehouse:
      - Note the OneLake storage size **before** creating the shortcut
        (step 1, or just before step 3).
      - Note it again **after** completing steps 3-4.
      - The size attributable to actual OneLake-managed data (e.g., any
        Delta tables you created separately) should be unchanged by the
        ~386 KB the shortcut exposes — the shortcut's files count toward
        what you can *browse*, but not toward OneLake's billed storage,
        because the bytes still live in `fabricf2landingsa`.

- [ ] **Sanity check via deletion (optional, destructive on the source):**
      if you want a stronger proof, delete one of the smaller source blobs
      (e.g. `asset_master.csv`) directly from `fabricf2landingsa` via
      `az storage blob delete`, then refresh the Lakehouse Files view — the
      file should disappear from the shortcut too, proving Fabric is reading
      live from the source rather than from a copy. Re-upload it afterwards
      with `upload_to_landing.ps1` if you do this.

## 6. Cost / cleanup notes

- [ ] The Shortcut itself adds no separate Azure billing — `fabricf2landingsa`
      continues to be billed at Standard LRS rates (~AUD $0.03/GB/month,
      negligible at ~386 KB) — see [COST_TRACKER.md](../COST_TRACKER.md).
- [ ] To tear down after the demo: delete the shortcut in the Lakehouse
      first, then `az storage account delete --name fabricf2landingsa
      --resource-group rg-fabric-sandbox` (this deletes the container and
      all 5 blobs too), and update `COST_TRACKER.md` accordingly.

## Out of scope

WorkerShield PDF upload to this (or another) landing-zone container is
handled separately and is not covered by this checklist.
