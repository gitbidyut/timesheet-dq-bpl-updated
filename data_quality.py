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


# ----------------------------------------------------
# Helper to format validation output
# ----------------------------------------------------

def build_issue(rule_name, df_subset, columns):
    records = (
        df_subset[columns]
        .head(20)  # limit to avoid huge JSON
        .to_dict(orient="records")
    )

    return {
        "rule": rule_name,
        "count": len(df_subset),
        "details": records
    }


# ----------------------------------------------------
# Load Data
# ----------------------------------------------------

try:
    files = [f for f in os.listdir(INPUT_PATH) if f.endswith(".csv")]
    if not files:
        raise ValueError("No CSV file found")

    df = pd.read_csv(os.path.join(INPUT_PATH, files[0]))

except Exception as e:
    print("Error reading input:", str(e))
    sys.exit(1)


# ----------------------------------------------------
# Required Columns
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
    failures.append({
        "rule": "Missing Columns",
        "details": missing_cols
    })
    status = "FAILED"
    result = {
        "status": status,
        "failures": failures,
        "warnings": warnings
    }
    os.makedirs(OUTPUT_PATH, exist_ok=True)
    with open(RESULT_FILE, "w") as f:
        json.dump(result, f, indent=2)
    sys.exit(1)


# ----------------------------------------------------
# Convert Types
# ----------------------------------------------------

df["Hours"] = pd.to_numeric(df["Hours"], errors="coerce")
df["Date"] = pd.to_datetime(df["Date"], errors="coerce")


# ----------------------------------------------------
# 1️⃣ Invalid Hours Rule
# ----------------------------------------------------

invalid_hours = df[(df["Hours"] <= 0) | (df["Hours"] > 24) | df["Hours"].isna()]

if not invalid_hours.empty:
    failures.append(
        build_issue(
            "Invalid Hours (<=0, >24, or null)",
            invalid_hours,
            ["Employee", "EmployeeNr", "Date", "Hours"]
        )
    )


# ----------------------------------------------------
# 2️⃣ Daily Hours > 24 Rule
# ----------------------------------------------------

daily_hours = (
    df.groupby(["EmployeeNr", "Date"])["Hours"]
      .sum()
      .reset_index()
      .rename(columns={"Hours": "TotalDailyHours"})
)

overbooked = daily_hours[daily_hours["TotalDailyHours"] > 24]

if not overbooked.empty:
    merged = df.merge(overbooked, on=["EmployeeNr", "Date"])

    failures.append(
        build_issue(
            "Daily Hours Exceed 24",
            merged,
            ["Employee", "EmployeeNr", "Date", "TotalDailyHours"]
        )
    )


# ----------------------------------------------------
# 3️⃣ Invalid Activity Code
# ----------------------------------------------------

VALID_ACTIVITY_CODES = {
    "DEV", "TEST", "MEETING", "TRAINING", "SUPPORT"
}

invalid_activity = df[~df["ActivityCode"].isin(VALID_ACTIVITY_CODES)]

if not invalid_activity.empty:
    failures.append(
        build_issue(
            "Invalid ActivityCode",
            invalid_activity,
            ["Employee", "EmployeeNr", "ActivityCode"]
        )
    )


# ----------------------------------------------------
# 4️⃣ Future Date Rule
# ----------------------------------------------------

future_dates = df[df["Date"] > pd.Timestamp.today()]

if not future_dates.empty:
    failures.append(
        build_issue(
            "Future Date Detected",
            future_dates,
            ["Employee", "EmployeeNr", "Date"]
        )
    )


# ----------------------------------------------------
# 5️⃣ Whitespace Warning
# ----------------------------------------------------

if "Description" in df.columns:
    space_rows = df[df["Description"].astype(str).str.match(r"^\s+|\s+$")]
    if not space_rows.empty:
        warnings.append(
            build_issue(
                "Leading/Trailing Spaces in Description",
                space_rows,
                ["Employee", "EmployeeNr", "Description"]
            )
        )


# ----------------------------------------------------
# Prepare Output
# ----------------------------------------------------

status = "FAILED" if failures else ("WARN" if warnings else "PASSED")

result = {
    "status": status
}