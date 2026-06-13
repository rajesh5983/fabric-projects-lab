"""Generate a messy ERP HR dataset for the azure-sql-hr Fabric Mirroring demo.

Produces CostCenters, Employees, Timesheets, and PayRuns as CSV files (with a
header row) under ./output/, plus a matching sql/schema.sql. The dataset is
intentionally denormalized and inconsistently named to mirror a legacy ERP
extract: mixed column-naming conventions, repeated/duplicated records, NULLs,
orphaned references, and internally inconsistent values (e.g. NetPay !=
GrossPay - Deductions). Each table has a single-column primary key (required
for Fabric Mirroring); Employees uses a RowID surrogate key since EmpID has
intentional duplicates.

Column order in each CSV matches sql/schema.sql exactly, so the data can be
bulk-loaded with `bcp ... -c -t, -F 2` (ordinal load, skipping the header row).
Text fields are scrubbed of commas/newlines so that naive comma-delimited
bcp loading is safe.
"""

import csv
import random
from datetime import date, timedelta
from pathlib import Path

from faker import Faker

SEED = 42
TODAY = date(2026, 6, 13)

ROOT = Path(__file__).resolve().parent
OUTPUT_DIR = ROOT / "output"
SQL_DIR = ROOT / "sql"

N_BASE_COST_CENTERS = 150
N_COST_CENTERS = 2000
N_EMPLOYEES = 3000
N_EMPLOYEE_DUPLICATES = 90
N_TIMESHEETS = 5000
N_PAYRUNS = 4000

DEPARTMENTS = [
    "Finance", "Human Resources", "Information Technology", "Sales", "Operations",
    "Marketing", "Engineering", "Customer Support", "Legal", "Procurement",
    "Manufacturing", "Logistics", "Research and Development", "Quality Assurance", "Facilities",
]

REGION_VARIANTS = {
    "APAC": ["APAC", "Asia Pacific", "AU", "ANZ", "Asia-Pacific"],
    "EMEA": ["EMEA", "Europe", "EU"],
    "AMER": ["AMER", "Americas", "US", "NA"],
}

# Same logical name rendered inconsistently - the hallmark of a "messy ERP".
NAME_VARIANTS = [
    lambda n: n,
    lambda n: n.upper(),
    lambda n: n.lower(),
    lambda n: f"{n} Dept.",
    lambda n: "".join(w[0] for w in n.split()).upper(),
    lambda n: f"{n}  ",
]

ACTIVE_FLAG_VARIANTS = ["Y", "N", "1", "0", "True", "False", "yes", "no", "TRUE", "FALSE"]
STATUS_VARIANTS_ACTIVE = ["Active", "ACTIVE", "active", "On Leave", "on_leave", "OnLeave"]
STATUS_VARIANTS_TERMINATED = ["Terminated", "TERMINATED", "terminated"]
PAY_FREQ_VARIANTS = ["Weekly", "WEEKLY", "weekly", "BiWeekly", "Bi-Weekly", "biweekly", "Monthly", "MONTHLY", "monthly"]
TIMESHEET_STATUS_VARIANTS = [
    "Submitted", "SUBMITTED", "submitted", "Approved", "APPROVED", "approved",
    "Pending", "PENDING", "pending", "Rejected", "rejected",
]
CURRENCY_VARIANTS = ["AUD", "aud", "Aud", "Australian Dollar"]
PAYRUN_STATUS_VARIANTS = ["Processed", "PROCESSED", "processed", "Pending", "PENDING", "pending"]

# Codes that never appear in CostCenters.csv - used to simulate dangling references.
INVALID_CC_CODES = [f"CC-{9000 + i}" for i in range(20)]

PROJECT_CODES = [f"PRJ-{1000 + i}" for i in range(30)]

HIRE_START = TODAY - timedelta(days=365 * 10)
HIRE_END = TODAY - timedelta(days=30)


def clean(value):
    """Strip characters that would break naive comma-delimited bcp loads."""
    if value is None or value == "":
        return ""
    return str(value).replace(",", " ").replace("\n", " ").replace("\r", " ")


def random_date(rng, start, end):
    span = (end - start).days
    return start + timedelta(days=rng.randint(0, max(span, 0)))


def write_csv(path, rows, columns):
    fieldnames = [name for name, _ in columns]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def write_schema_sql(path, tables, primary_keys):
    lines = [
        "-- Messy ERP HR schema for the azure-sql-hr Fabric Mirroring demo.",
        "-- Intentionally denormalized and inconsistently named (no FKs/NOT NULL",
        "-- beyond primary keys) to mirror a legacy ERP extract. Each table has a",
        "-- primary key so Fabric Mirroring can replicate it; Employees uses a",
        "-- RowID surrogate key since EmpID has intentional duplicates. Column",
        "-- order matches the generated CSVs for ordinal bcp loading (-F 2).",
        "",
    ]
    for table_name, columns in tables.items():
        pk_col = primary_keys.get(table_name)
        lines.append(f"IF OBJECT_ID('dbo.{table_name}', 'U') IS NOT NULL DROP TABLE dbo.{table_name};")
        lines.append(f"CREATE TABLE dbo.{table_name} (")
        col_defs = [
            f"    {name} {sql_type} {'NOT NULL' if name == pk_col else 'NULL'}"
            for name, sql_type in columns
        ]
        if pk_col:
            col_defs.append(f"    CONSTRAINT PK_{table_name} PRIMARY KEY ({pk_col})")
        lines.append(",\n".join(col_defs))
        lines.append(");")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------------------
# CostCenters
# ---------------------------------------------------------------------------

COST_CENTER_COLUMNS = [
    ("CostCenterID", "INT"),
    ("cc_code", "NVARCHAR(20)"),
    ("CostCenterName", "NVARCHAR(100)"),
    ("region", "NVARCHAR(50)"),
    ("ManagerEmail", "NVARCHAR(100)"),
    ("IsActive", "NVARCHAR(10)"),
    ("ParentCostCenterCode", "NVARCHAR(20)"),
]


def generate_cost_centers(fake, rng):
    base = []
    for i in range(N_BASE_COST_CENTERS):
        base.append({
            "cc_code": f"CC-{1000 + i}",
            "dept": rng.choice(DEPARTMENTS),
            "city": fake.city(),
            "region_family": rng.choice(list(REGION_VARIANTS.keys())),
        })

    rows = []
    for cc_id in range(1, N_COST_CENTERS + 1):
        b = rng.choice(base)
        name = rng.choice(NAME_VARIANTS)(f"{b['dept']} - {b['city']}")
        region = rng.choice(REGION_VARIANTS[b["region_family"]])
        manager_email = "" if rng.random() < 0.2 else fake.company_email()

        r = rng.random()
        if r < 0.1:
            parent = rng.choice(base)["cc_code"]
        elif r < 0.12:
            parent = rng.choice(INVALID_CC_CODES)
        else:
            parent = ""

        rows.append({
            "CostCenterID": cc_id,
            "cc_code": b["cc_code"],
            "CostCenterName": clean(name),
            "region": region,
            "ManagerEmail": manager_email,
            "IsActive": rng.choice(ACTIVE_FLAG_VARIANTS),
            "ParentCostCenterCode": parent,
        })

    return rows, [b["cc_code"] for b in base]


# ---------------------------------------------------------------------------
# Employees
# ---------------------------------------------------------------------------

EMPLOYEE_COLUMNS = [
    ("RowID", "INT"),
    ("EmpID", "INT"),
    ("emp_no", "NVARCHAR(20)"),
    ("FullName", "NVARCHAR(100)"),
    ("first_name", "NVARCHAR(50)"),
    ("last_name", "NVARCHAR(50)"),
    ("Email", "NVARCHAR(100)"),
    ("HireDate", "DATE"),
    ("TerminationDate", "DATE"),
    ("DeptName", "NVARCHAR(50)"),
    ("CostCenterCode", "NVARCHAR(20)"),
    ("ManagerEmpID", "INT"),
    ("status", "NVARCHAR(20)"),
    ("Country", "NVARCHAR(100)"),
    ("State", "NVARCHAR(50)"),
    ("City", "NVARCHAR(50)"),
    ("BaseSalary", "DECIMAL(12,2)"),
    ("PayFrequency", "NVARCHAR(20)"),
]


def _generate_employee_row(emp_id, fake, rng, cc_codes, n_unique):
    first, last = fake.first_name(), fake.last_name()
    full_name = f"{first} {last}"

    # Some rows only carry FullName, some only first/last - never both consistently.
    style = rng.random()
    if style < 0.4:
        row_full, row_first, row_last = full_name, "", ""
    elif style < 0.8:
        row_full, row_first, row_last = "", first, last
    else:
        row_full, row_first, row_last = full_name, first, last

    hire_date = random_date(rng, HIRE_START, HIRE_END)
    terminated = rng.random() < 0.08
    termination_date = random_date(rng, hire_date, TODAY) if terminated else ""

    if terminated:
        status = rng.choice(STATUS_VARIANTS_ACTIVE) if rng.random() < 0.3 else rng.choice(STATUS_VARIANTS_TERMINATED)
    else:
        status = rng.choice(STATUS_VARIANTS_ACTIVE) if rng.random() < 0.95 else rng.choice(STATUS_VARIANTS_TERMINATED)

    r = rng.random()
    if r < 0.95:
        cost_center_code = rng.choice(cc_codes)
    elif r < 0.975:
        cost_center_code = rng.choice(INVALID_CC_CODES)
    else:
        cost_center_code = ""

    if emp_id == 1:
        manager_emp_id = ""
    else:
        r = rng.random()
        if r < 0.1:
            manager_emp_id = ""
        elif r < 0.95:
            manager_emp_id = rng.randint(1, emp_id - 1)
        else:
            manager_emp_id = rng.randint(n_unique + 1, n_unique + 200)

    base_salary = "" if rng.random() < 0.05 else round(rng.uniform(45000, 180000), 2)

    return {
        "EmpID": emp_id,
        "emp_no": "" if rng.random() < 0.15 else f"E{emp_id:06d}",
        "FullName": clean(row_full),
        "first_name": clean(row_first),
        "last_name": clean(row_last),
        "Email": "" if rng.random() < 0.1 else fake.email(),
        "HireDate": hire_date.isoformat(),
        "TerminationDate": termination_date.isoformat() if termination_date else "",
        "DeptName": clean(rng.choice(NAME_VARIANTS)(rng.choice(DEPARTMENTS))),
        "CostCenterCode": cost_center_code,
        "ManagerEmpID": manager_emp_id,
        "status": status,
        "Country": clean(fake.country()),
        "State": fake.state_abbr(),
        "City": clean(fake.city()),
        "BaseSalary": base_salary,
        "PayFrequency": rng.choice(PAY_FREQ_VARIANTS),
        # Internal lookup fields for downstream tables - dropped by write_csv.
        "_full_name_actual": full_name,
    }


def generate_employees(fake, rng, cc_codes):
    n_unique = N_EMPLOYEES - N_EMPLOYEE_DUPLICATES
    rows = [_generate_employee_row(emp_id, fake, rng, cc_codes, n_unique) for emp_id in range(1, n_unique + 1)]

    # Duplicate rows: same EmpID, freshly (and often inconsistently) generated details.
    for _ in range(N_EMPLOYEE_DUPLICATES):
        emp_id = rng.randint(1, n_unique)
        rows.append(_generate_employee_row(emp_id, fake, rng, cc_codes, n_unique))

    # Surrogate row key - EmpID has intentional duplicates, so it can't be a PK.
    for row_id, row in enumerate(rows, start=1):
        row["RowID"] = row_id

    return rows


# ---------------------------------------------------------------------------
# Timesheets
# ---------------------------------------------------------------------------

TIMESHEET_COLUMNS = [
    ("TimesheetID", "INT"),
    ("EmpID", "INT"),
    ("EmployeeName", "NVARCHAR(100)"),
    ("week_ending", "DATE"),
    ("HoursWorked", "DECIMAL(6,2)"),
    ("OvertimeHrs", "DECIMAL(5,2)"),
    ("ProjectCode", "NVARCHAR(20)"),
    ("CostCenter", "NVARCHAR(20)"),
    ("ApprovedBy", "NVARCHAR(100)"),
    ("TimesheetStatus", "NVARCHAR(20)"),
]


def _project_code_variant(code, rng):
    r = rng.random()
    if r < 0.4:
        return code
    if r < 0.7:
        return code.lower()
    return code.replace("PRJ-", "Proj_")


def generate_timesheets(fake, rng, employee_lookup, emp_ids, cc_codes):
    week_anchor = TODAY - timedelta(weeks=52)
    max_emp_id = max(emp_ids)
    rows = []

    for ts_id in range(1, N_TIMESHEETS + 1):
        if rng.random() < 0.03:
            emp_id = rng.randint(max_emp_id + 1, max_emp_id + 300)
            emp = None
        else:
            emp_id = rng.choice(emp_ids)
            emp = employee_lookup.get(emp_id)

        employee_name = emp["full_name"] if (emp and rng.random() > 0.1) else ""

        week_ending = week_anchor + timedelta(weeks=rng.randint(0, 51), days=rng.randint(0, 6))

        r = rng.random()
        if r < 0.03:
            hours = ""
        elif r < 0.05:
            hours = round(rng.uniform(-5, 0), 2)
        elif r < 0.07:
            hours = round(rng.uniform(80, 120), 2)
        else:
            hours = round(rng.uniform(20, 45), 2)

        overtime = "" if rng.random() < 0.5 else round(rng.uniform(0, 15), 2)

        if emp and rng.random() < 0.9:
            cost_center = emp["cost_center_code"]
        else:
            cost_center = rng.choice(cc_codes)

        rows.append({
            "TimesheetID": ts_id,
            "EmpID": emp_id,
            "EmployeeName": clean(employee_name),
            "week_ending": week_ending.isoformat(),
            "HoursWorked": hours,
            "OvertimeHrs": overtime,
            "ProjectCode": _project_code_variant(rng.choice(PROJECT_CODES), rng),
            "CostCenter": cost_center,
            "ApprovedBy": "" if rng.random() < 0.3 else clean(fake.name()),
            "TimesheetStatus": rng.choice(TIMESHEET_STATUS_VARIANTS),
        })

    return rows


# ---------------------------------------------------------------------------
# PayRuns
# ---------------------------------------------------------------------------

PAYRUN_COLUMNS = [
    ("PayRunID", "INT"),
    ("EmpID", "INT"),
    ("emp_full_name", "NVARCHAR(100)"),
    ("PayPeriodStart", "DATE"),
    ("PayPeriodEnd", "DATE"),
    ("GrossPay", "DECIMAL(12,2)"),
    ("Deductions", "DECIMAL(12,2)"),
    ("NetPay", "DECIMAL(12,2)"),
    ("CostCenterCode", "NVARCHAR(20)"),
    ("pay_date", "DATE"),
    ("Currency", "NVARCHAR(20)"),
    ("RunStatus", "NVARCHAR(20)"),
]


def _month_bounds(anchor, months_back):
    year, month = anchor.year, anchor.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    start = date(year, month, 1)
    end = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
    return start, end


def generate_payruns(fake, rng, employee_lookup, emp_ids, cc_codes):
    max_emp_id = max(emp_ids)
    rows = []

    for pr_id in range(1, N_PAYRUNS + 1):
        if rng.random() < 0.03:
            emp_id = rng.randint(max_emp_id + 1, max_emp_id + 300)
            emp = None
        else:
            emp_id = rng.choice(emp_ids)
            emp = employee_lookup.get(emp_id)

        emp_full_name = emp["full_name"] if (emp and rng.random() > 0.15) else ""

        period_start, period_end = _month_bounds(TODAY, rng.randint(1, 12))
        pay_date = period_end + timedelta(days=rng.randint(3, 7))

        if emp and emp["base_salary"]:
            gross = round(emp["base_salary"] / 12 * rng.uniform(0.95, 1.05), 2)
        else:
            gross = round(rng.uniform(3000, 12000), 2)

        deductions = "" if rng.random() < 0.1 else round(gross * rng.uniform(0.15, 0.35), 2)

        if rng.random() < 0.05:
            # Data-entry error: NetPay unrelated to GrossPay - Deductions.
            net = round(gross * rng.uniform(0.5, 1.5), 2)
        else:
            net = round(gross - (deductions if deductions != "" else 0), 2)

        if emp and rng.random() < 0.92:
            cost_center_code = emp["cost_center_code"]
        else:
            cost_center_code = rng.choice(cc_codes)

        rows.append({
            "PayRunID": pr_id,
            "EmpID": emp_id,
            "emp_full_name": clean(emp_full_name),
            "PayPeriodStart": period_start.isoformat(),
            "PayPeriodEnd": period_end.isoformat(),
            "GrossPay": gross,
            "Deductions": deductions,
            "NetPay": net,
            "CostCenterCode": cost_center_code,
            "pay_date": pay_date.isoformat(),
            "Currency": rng.choice(CURRENCY_VARIANTS),
            "RunStatus": rng.choice(PAYRUN_STATUS_VARIANTS),
        })

    return rows


PRIMARY_KEYS = {
    "CostCenters": "CostCenterID",
    "Employees": "RowID",
    "Timesheets": "TimesheetID",
    "PayRuns": "PayRunID",
}


def main():
    rng = random.Random(SEED)
    fake = Faker()
    Faker.seed(SEED)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SQL_DIR.mkdir(parents=True, exist_ok=True)

    print("azure-sql-hr - messy ERP HR data generation")
    print(f"Seed: {SEED} | Anchor date: {TODAY.isoformat()}")
    print()

    print("[1/4] CostCenters.csv")
    cost_center_rows, cc_codes = generate_cost_centers(fake, rng)
    write_csv(OUTPUT_DIR / "CostCenters.csv", cost_center_rows, COST_CENTER_COLUMNS)
    print(f"      -> {len(cost_center_rows)} rows ({len(set(cc_codes))} distinct cc_codes)")

    print("[2/4] Employees.csv")
    employee_rows = generate_employees(fake, rng, cc_codes)
    write_csv(OUTPUT_DIR / "Employees.csv", employee_rows, EMPLOYEE_COLUMNS)
    n_distinct_ids = len(set(r["EmpID"] for r in employee_rows))
    print(f"      -> {len(employee_rows)} rows ({len(employee_rows) - n_distinct_ids} duplicate EmpIDs)")

    employee_lookup = {}
    for row in employee_rows:
        employee_lookup.setdefault(row["EmpID"], {
            "full_name": row["_full_name_actual"],
            "cost_center_code": row["CostCenterCode"],
            "base_salary": row["BaseSalary"] if row["BaseSalary"] != "" else None,
        })
    emp_ids = [row["EmpID"] for row in employee_rows]

    print("[3/4] Timesheets.csv")
    timesheet_rows = generate_timesheets(fake, rng, employee_lookup, emp_ids, cc_codes)
    write_csv(OUTPUT_DIR / "Timesheets.csv", timesheet_rows, TIMESHEET_COLUMNS)
    print(f"      -> {len(timesheet_rows)} rows")

    print("[4/4] PayRuns.csv")
    payrun_rows = generate_payruns(fake, rng, employee_lookup, emp_ids, cc_codes)
    write_csv(OUTPUT_DIR / "PayRuns.csv", payrun_rows, PAYRUN_COLUMNS)
    print(f"      -> {len(payrun_rows)} rows")

    write_schema_sql(SQL_DIR / "schema.sql", {
        "CostCenters": COST_CENTER_COLUMNS,
        "Employees": EMPLOYEE_COLUMNS,
        "Timesheets": TIMESHEET_COLUMNS,
        "PayRuns": PAYRUN_COLUMNS,
    }, PRIMARY_KEYS)

    print()
    print(f"Output CSVs: {OUTPUT_DIR}")
    print(f"Schema DDL:  {SQL_DIR / 'schema.sql'}")
    print(f"Seed: {SEED} | Reproducible: YES")


if __name__ == "__main__":
    main()
