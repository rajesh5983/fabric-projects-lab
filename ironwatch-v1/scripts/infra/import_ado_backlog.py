"""Import docs/azure-boards/ironwatch_v1_v2_backlog.csv into Azure Boards via az CLI.

Each Epic row creates an Epic work item; each following User Story row
creates an Issue work item (see STORY_WORK_ITEM_TYPE) linked as a child of
the most recently created Epic.
Fails fast on the first az CLI error so a partial import is always visible
rather than silently continuing into a broken hierarchy.

IDEMPOTENT-UNSAFE: every run creates new work items unconditionally: there
is no check for existing items with matching titles. Re-running against a
project that already has this backlog imported will duplicate every Epic
and Issue rather than update them. If re-importing after CSV edits, delete
the existing items first (or add matching logic before re-running).
"""
from __future__ import annotations

import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path

ORGANIZATION = "https://dev.azure.com/modernanalyticslab"
PROJECT = "IronWatch"
CSV_PATH = Path(__file__).resolve().parents[2] / "docs" / "azure-boards" / "ironwatch_v1_v2_backlog.csv"

# Generous enough for normal az CLI latency, short enough to fail fast
# instead of hanging indefinitely (e.g. an unexpected interactive auth
# prompt) — that exact failure mode stalled an `az devops login` run this
# session until it was manually killed.
AZ_TIMEOUT_SECONDS = 60

# IronWatch uses ADO's Basic process template (Epic/Issue/Task), which has no
# "User Story" type. The CSV's "User Story" rows map to "Issue" on create.
STORY_WORK_ITEM_TYPE = "Issue"

AZ_EXECUTABLE = shutil.which("az")
if AZ_EXECUTABLE is None:
    sys.exit("FAILED: 'az' not found on PATH")

# Reconfigure stdout for the arrows/dashes below rather than crashing on the
# Windows console's cp1252 default.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# az.cmd is a batch-file wrapper; on this Windows setup, non-ASCII characters
# in CLI args get silently dropped somewhere in that wrapper's argument
# marshalling (confirmed by creating a work item with "->" in the title and
# finding the arrow missing, with no replacement, in the stored ADO field —
# not just a console-display issue). Sanitize to ASCII equivalents before
# they ever reach the CLI so what's created matches source intent.
_CLI_SAFE_REPLACEMENTS = {
    "—": "-",    # em dash —
    "→": "->",   # right arrow →
    "§": "Sec ",  # section sign §
}


def _cli_safe(text: str) -> str:
    for char, replacement in _CLI_SAFE_REPLACEMENTS.items():
        text = text.replace(char, replacement)
    return text


def run_az(args: list[str], include_project: bool) -> dict:
    # az's own warnings/output on Windows are sometimes emitted in the console's
    # codepage (cp1252) rather than UTF-8, which breaks a strict UTF-8 decode
    # when our descriptions contain em dashes etc. errors="replace" keeps the
    # reader thread alive instead of losing the whole output to a crash.
    full_args = [AZ_EXECUTABLE, *args, "--organization", ORGANIZATION]
    if include_project:
        full_args += ["--project", PROJECT]
    full_args += ["--output", "json"]
    try:
        result = subprocess.run(
            full_args,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=AZ_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print(f"FAILED: az {' '.join(args)} (timed out after {AZ_TIMEOUT_SECONDS}s)", file=sys.stderr)
        sys.exit(1)
    if result.returncode != 0:
        print(f"FAILED: az {' '.join(args)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return json.loads(result.stdout)


def create_work_item(work_item_type: str, title: str, description: str, tags: str) -> int:
    args = [
        "boards", "work-item", "create",
        "--type", work_item_type,
        "--title", title,
        "--description", description,
    ]
    if tags:
        args += ["--fields", f"System.Tags={tags.replace(';', '; ')}"]
    return run_az(args, include_project=True)["id"]


def link_parent(child_id: int, parent_id: int) -> None:
    # work-item relation add doesn't accept --project (work item IDs are
    # unique per-organization, not per-project).
    run_az([
        "boards", "work-item", "relation", "add",
        "--id", str(child_id),
        "--relation-type", "parent",
        "--target-id", str(parent_id),
    ], include_project=False)


def _validate_rows(rows: list[dict]) -> None:
    """Side-effect-free preflight so a bad row can't leave earlier rows'
    work items orphaned in Azure — the script is documented as
    idempotent-unsafe, so a partial run isn't cleanly re-runnable."""
    seen_epic = False
    for i, row in enumerate(rows, start=2):  # +1 header, +1 to 1-index
        wi_type = row["Work Item Type"]
        if wi_type == "Epic":
            if not row["Title 1"]:
                sys.exit(f"FAILED: CSV row {i} is an Epic with no Title 1")
            seen_epic = True
        elif wi_type == "User Story":
            if not row["Title 2"]:
                sys.exit(f"FAILED: CSV row {i} is a User Story with no Title 2")
            if not seen_epic:
                sys.exit(f"FAILED: CSV row {i} (User Story) has no preceding Epic")
        else:
            sys.exit(f"FAILED: CSV row {i} has unknown Work Item Type {wi_type!r}")


def main() -> None:
    with CSV_PATH.open(newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    _validate_rows(rows)

    csv_epic_count = sum(1 for r in rows if r["Work Item Type"] == "Epic")
    csv_story_count = sum(1 for r in rows if r["Work Item Type"] == "User Story")

    epics_created = 0
    stories_created = 0
    links_created = 0
    current_epic_id: int | None = None
    current_epic_title = ""

    for row in rows:
        wi_type = row["Work Item Type"]
        tags = row["Tags"]
        description = _cli_safe(row["Description"])

        if wi_type == "Epic":
            title = _cli_safe(row["Title 1"])
            epic_id = create_work_item("Epic", title, description, tags)
            print(f"Created Epic {epic_id}: {title}")
            current_epic_id = epic_id
            current_epic_title = title
            epics_created += 1

        else:  # "User Story" — the only other type _validate_rows allows
            title = _cli_safe(row["Title 2"])
            story_id = create_work_item(STORY_WORK_ITEM_TYPE, title, description, tags)
            print(f"Created {STORY_WORK_ITEM_TYPE} {story_id}: {title}")
            stories_created += 1

            link_parent(story_id, current_epic_id)
            print(f"  Linked Story {story_id} -> parent Epic {current_epic_id} ({current_epic_title})")
            links_created += 1

    print()
    print("=== SUMMARY ===")
    print(f"Epics created:         {epics_created} (CSV has {csv_epic_count})")
    print(f"Stories created:       {stories_created} (CSV has {csv_story_count})")
    print(f"Parent links created:  {links_created} (expected {csv_story_count})")

    if (
        epics_created != csv_epic_count
        or stories_created != csv_story_count
        or links_created != csv_story_count
    ):
        print("MISMATCH between created counts and CSV row counts.", file=sys.stderr)
        sys.exit(1)

    print("Counts match the CSV. Import complete.")


if __name__ == "__main__":
    main()
