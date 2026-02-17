import os
import sys
import json
import pandas as pd
from datetime import datetime

INPUT_PATH = "/opt/ml/processing/input"
OUTPUT_PATH = "/opt/ml/processing/output"
RESULT_FILE = os.path.join(OUTPUT_PATH, "dq_result.json")

failures = []
warnings = []
affected_employee_set = set()


# ----------------------------------------------------
# Helper Functions
# ----------------------------------------------------

def fail(message):
    print(f"[FAIL] {message}")
    failures.append(message)


def warn(message):
    print(f"[WARN] {message}")
    warnings.append(message)


def collect_affected_employees(sub_df):
    if "Employee" in sub_df.columns and "EmployeeNr" in sub_df.columns:
        pairs = sub_df[["Employee", "EmployeeNr"]].drop_duplicates()
        for _, row in pairs.iterrows():
            affected_employee_set.add(
                (str(row["Employee"]), str(row["EmployeeNr"]))
            )


# ----------------------------------------------------
# Load Input File
# ----------------------------------------------------

try:
    files = [f for f in os.listdir(INPUT_PATH) if f.endswith(".csv")]
    if not files:
        raise ValueError("No CSV file found in input directory")

    input_file = os.path.join(INPUT_PATH, files[0])
    print(f"Reading input file: {input_file}")

    df = pd.read_csv(input_file)

except Exception as e:
    print("Error reading input:", str(e))
    sys.exit(1)


# ----------------------------------------------------
# 1. Schema Validation
# ----------------------------------------------------

REQUIRED_COLUMNS = [
    "Employee",
    "EmployeeNr",
    "Date",
    "Hours",
    "ProjectCode",
    "ActivityCode"
]

missing_cols = [c for c in REQUIRED_COLUMNS if c not in df.columns]
if missing_cols:
    fail(f"Missing required columns: {missing_cols}")
    result = {
        "status": "FAILED",
        "failures": failures,
        "warnings": warnings
    }
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    sys.exit(1)


# ----------------------------------------------------
# 2. Null / Empty Checks
# ----------------------------------------------------

NULL_THRESHOLD = 0.05  # 5%

for col in REQUIRED_COLUMNS:
    null_ratio = df[col].isna().mean()
    if null_ratio > NULL_THRESHOLD:
        fail(f"{col} has {null_ratio:.1%} null values")


# ----------------------------------------------------
# 3. Hours Validation
# ----------------------------------------------------

df["Hours"] = pd.to_numeric(df["Hours"], errors="coerce")

invalid_hours_df = df[(df["Hours"] <= 0) | (df["Hours"] > 24) | df["Hours"].isna()]

if not invalid_hours_df.empty:
    fail(f"{len(invalid_hours_df)} rows have invalid Hours (<=0 or >24)")
    collect_affected_employees(invalid_hours_df)


# ----------------------------------------------------
# 4. Daily Hours > 24 per Employee
# ----------------------------------------------------

df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

daily_hours = df.groupby(["EmployeeNr", "Date"])["Hours"].sum()

overbooked = daily_hours[daily_hours > 24]

if not overbooked.empty:
    fail(f"{len(overbooked)} employee-days exceed 24 hours")
    overbooked_df = df[df.set_index(["EmployeeNr", "Date"]).index.isin(overbooked.index)]
    collect_affected_employees(overbooked_df)


# ----------------------------------------------------
# 5. Activity Code Validation
# ----------------------------------------------------

VALID_ACTIVITY_CODES = {
    "DEV", "TEST", "MEETING", "TRAINING", "SUPPORT"
}

invalid_activity_df = df[~df["ActivityCode"].isin(VALID_ACTIVITY_CODES)]

if invalid_activity_df.mean().size > 0:
    invalid_ratio = len(invalid_activity_df) / len(df)
    if invalid_ratio > 0.01:
        fail(f"{invalid_ratio:.1%} rows have invalid ActivityCode")
        collect_affected_employees(invalid_activity_df)


# ----------------------------------------------------
# 6. Future Date Check
# ----------------------------------------------------

future_df = df[df["Date"] > pd.Timestamp.today()]

if not future_df.empty:
    fail(f"{len(future_df)} rows contain future dates")
    collect_affected_employees(future_df)


# ----------------------------------------------------
# 7. Whitespace Check (Description)
# ----------------------------------------------------

if "Description" in df.columns:
    space_ratio = df["Description"].astype(str).str.match(r"^\s+|\s+$").mean()
    if space_ratio > 0.02:
        warn(f"Description has leading/trailing spaces in {space_ratio:.1%} of rows")


# ----------------------------------------------------
# 8. Duplicate Entries
# ----------------------------------------------------

dup_count = df.duplicated(
    subset=["EmployeeNr", "Date", "ProjectCode"]
).sum()

if dup_count > 0:
    warn(f"{dup_count} duplicate timesheet entries detected")


# ----------------------------------------------------
# Prepare Output
# ----------------------------------------------------

unique_employees = df["EmployeeNr"].nunique()

affected_employees = [
    {"Employee": emp, "EmployeeNr": empnr}
    for emp, empnr in affected_employee_set
]

status = "FAILED" if failures else ("WARN" if warnings else "PASSED")

result = {
    "status": status,
    "row_count": len(df),
    "unique_employees": unique_employees,
    "affected_employee_count": len(affected_employees),
    "affected_employees": affected_employees,
    "failures": failures,
    "warnings": warnings,
    "timestamp": datetime.utcnow().isoformat()
}

os.makedirs(OUTPUT_PATH, exist_ok=True)

with open(RESULT_FILE, "w") as f:
    json.dump(result, f, indent=2)

print("DQ result written to:", RESULT_FILE)

# ----------------------------------------------------
# Exit Code (important for pipeline control)
# ----------------------------------------------------

if failures:
    sys.exit(1)
else:
    sys.exit(0)
