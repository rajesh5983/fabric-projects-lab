# Fabric CLI Setup

This project uses the Microsoft Fabric CLI as the preferred deployment path where the CLI can perform actions safely.

## Prerequisites

- Python 3.10 or higher
- Access to the target Microsoft Fabric tenant
- Access to the target Fabric workspace
- Permission to create or update Fabric items if you plan to create a Lakehouse or upload files

## Install Fabric CLI

Install the Fabric CLI with pip:

```bash
pip install ms-fabric-cli
```

Verify that the `fab` command is available:

```bash
fab --version
```

## Authenticate

Sign in to Microsoft Fabric:

```bash
fab auth login
```

Choose the login method appropriate for your environment. For local development, interactive browser login is usually the simplest option.

## Validate Access

List the Fabric workspaces available to your signed-in identity:

```bash
fab ls
```

Confirm that the target workspace appears in the output before running deployment steps.

## Notes

- The signed-in user or service principal must have access to the target Fabric workspace.
- Workspace item creation requires suitable workspace permissions, such as Member, Contributor, or Admin depending on the target action.
- Do not store credentials, tokens, tenant IDs, client secrets, or other sensitive values in this repository.
- Keep synthetic data loads separate from production data.
