-- Messy ERP HR schema for the azure-sql-hr Fabric Mirroring demo.
-- Intentionally denormalized and inconsistently named (no FKs/NOT NULL
-- beyond primary keys) to mirror a legacy ERP extract. Each table has a
-- primary key so Fabric Mirroring can replicate it; Employees uses a
-- RowID surrogate key since EmpID has intentional duplicates. Column
-- order matches the generated CSVs for ordinal bcp loading (-F 2).

IF OBJECT_ID('dbo.CostCenters', 'U') IS NOT NULL DROP TABLE dbo.CostCenters;
CREATE TABLE dbo.CostCenters (
    CostCenterID INT NOT NULL,
    cc_code NVARCHAR(20) NULL,
    CostCenterName NVARCHAR(100) NULL,
    region NVARCHAR(50) NULL,
    ManagerEmail NVARCHAR(100) NULL,
    IsActive NVARCHAR(10) NULL,
    ParentCostCenterCode NVARCHAR(20) NULL,
    CONSTRAINT PK_CostCenters PRIMARY KEY (CostCenterID)
);

IF OBJECT_ID('dbo.Employees', 'U') IS NOT NULL DROP TABLE dbo.Employees;
CREATE TABLE dbo.Employees (
    RowID INT NOT NULL,
    EmpID INT NULL,
    emp_no NVARCHAR(20) NULL,
    FullName NVARCHAR(100) NULL,
    first_name NVARCHAR(50) NULL,
    last_name NVARCHAR(50) NULL,
    Email NVARCHAR(100) NULL,
    HireDate DATE NULL,
    TerminationDate DATE NULL,
    DeptName NVARCHAR(50) NULL,
    CostCenterCode NVARCHAR(20) NULL,
    ManagerEmpID INT NULL,
    status NVARCHAR(20) NULL,
    Country NVARCHAR(100) NULL,
    State NVARCHAR(50) NULL,
    City NVARCHAR(50) NULL,
    BaseSalary DECIMAL(12,2) NULL,
    PayFrequency NVARCHAR(20) NULL,
    CONSTRAINT PK_Employees PRIMARY KEY (RowID)
);

IF OBJECT_ID('dbo.Timesheets', 'U') IS NOT NULL DROP TABLE dbo.Timesheets;
CREATE TABLE dbo.Timesheets (
    TimesheetID INT NOT NULL,
    EmpID INT NULL,
    EmployeeName NVARCHAR(100) NULL,
    week_ending DATE NULL,
    HoursWorked DECIMAL(6,2) NULL,
    OvertimeHrs DECIMAL(5,2) NULL,
    ProjectCode NVARCHAR(20) NULL,
    CostCenter NVARCHAR(20) NULL,
    ApprovedBy NVARCHAR(100) NULL,
    TimesheetStatus NVARCHAR(20) NULL,
    CONSTRAINT PK_Timesheets PRIMARY KEY (TimesheetID)
);

IF OBJECT_ID('dbo.PayRuns', 'U') IS NOT NULL DROP TABLE dbo.PayRuns;
CREATE TABLE dbo.PayRuns (
    PayRunID INT NOT NULL,
    EmpID INT NULL,
    emp_full_name NVARCHAR(100) NULL,
    PayPeriodStart DATE NULL,
    PayPeriodEnd DATE NULL,
    GrossPay DECIMAL(12,2) NULL,
    Deductions DECIMAL(12,2) NULL,
    NetPay DECIMAL(12,2) NULL,
    CostCenterCode NVARCHAR(20) NULL,
    pay_date DATE NULL,
    Currency NVARCHAR(20) NULL,
    RunStatus NVARCHAR(20) NULL,
    CONSTRAINT PK_PayRuns PRIMARY KEY (PayRunID)
);
