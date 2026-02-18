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


# --------------------------------------------------
# Helper: Safe issue builder
# --------------------------------------------------
def build_issue(rule_name, df_subset, columns):
    valid_columns = [c for c in columns if c in df_subset.columns]

    records = (
        df_subset[valid_columns]
        .head(20)  # limit large outputs
        .to_dict(orient="records")
    )

    return {
        "rule": rule_name,
        "count": len(df_subset),
        "details": records
    }


# --------------------------------------------------
# MAIN LOGIC (wrapped safely)
# --------------------------------------------------
try:
    print("=== Data Quality Script Started ===")

    # --------------------------------------------------
    # Load input file
    # --------------------------------------------------
    files = [f for f in os.listdir(INPUT_PATH) if f.endswith(".csv")]
    print("Files found:", files)

    if not files:
        raise ValueError("No CSV file found in input directory")

    input_file = os.path.join(INPUT_PATH, files[0])
    print("Reading file:", input_file)

    df = pd.read_csv(input_file)

    print("DataFrame shape:", df.shape)
    print("Columns:", df.columns.tolist())

    # --------------------------------------------------
    # Required Columns
    # --------------------------------------------------
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
        raise ValueError("Missing required columns")

    # --------------------------------------------------
    # Type Conversion
    # --------------------------------------------------
    df["Hours"] = pd.to_numeric(df["Hours"], errors="coerce")
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce")

    # --------------------------------------------------
    # 1️⃣ Invalid Hours Rule
    # --------------------------------------------------
    invalid_hours = df[
        (df["Hours"] <= 0) |
        (df["Hours"] > 24) |
        (df["Hours"].isna())
    ]

    if not invalid_hours.empty:
        failures.append(
            build_issue(
                "Invalid Hours (<=0, >24, null)",
                invalid_hours,
                ["Employee", "EmployeeNr", "Date", "Hours"]
            )
        )

    # --------------------------------------------------
    # 2️⃣ Daily Hours > 24 Rule
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 3️⃣ Invalid Activity Code
    # --------------------------------------------------
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

    # --------------------------------------------------
    # 4️⃣ Future Date Rule
    # --------------------------------------------------
    future_dates = df[df["Date"] > pd.Timestamp.today()]

    if not future_dates.empty:
        failures.append(
            build_issue(
                "Future Date Detected",
                future_dates,
                ["Employee", "EmployeeNr", "Date"]
            )
        )

    # --------------------------------------------------
    # 5️⃣ Excessive Null Check (5%)
    # --------------------------------------------------
    NULL_THRESHOLD = 0.05

    for col in REQUIRED_COLUMNS:
        null_ratio = df[col].isna().mean()
        if null_ratio > NULL_THRESHOLD:
            failures.append({
                "rule": f"{col} has excessive nulls",
                "ratio": f"{null_ratio:.1%}"
            })

    # --------------------------------------------------
    # 6️⃣ Duplicate Warning
    # --------------------------------------------------
    dup_count = df.duplicated(
        subset=["EmployeeNr", "Date", "ProjectCode"]
    ).sum()

    if dup_count > 0:
        warnings.append({
            "rule": "Duplicate Entries",
            "count": int(dup_count)
        })

    # --------------------------------------------------
    # 7️⃣ Whitespace Warning
    # --------------------------------------------------
    if "Description" in df.columns:
        space_rows = df[
            df["Description"].astype(str).str.match(r"^\s+|\s+$")
        ]
        if not space_rows.empty:
            warnings.append(
                build_issue(
                    "Leading/Trailing Spaces in Description",
                    space_rows,
                    ["Employee", "EmployeeNr", "Description"]
                )
            )

except Exception as e:
    print("Unexpected error:", str(e))
    failures.append({
        "rule": "Unexpected Error",
        "details": str(e)
    })


# --------------------------------------------------
# ALWAYS WRITE OUTPUT
# --------------------------------------------------

status = "FAILED" if failures else ("WARN" if warnings else "PASSED")

result = {
    "status": status,
    "row_count": len(df) if "df" in locals() else 0,
    "unique_employees": df["EmployeeNr"].nunique() if "df" in locals() else 0,
    "failures": failures,
    "warnings": warnings,
    "timestamp": datetime.utcnow().isoformat()
}

os.makedirs(OUTPUT_PATH, exist_ok=True)

with open(RESULT_FILE, "w") as f:
    json.dump(result, f, indent=2)

print("DQ result written to:", RESULT_FILE)
print("Final Status:", status)

# Proper exit control
if status == "FAILED":
    sys.exit(1)
else:
    sys.exit(0)
