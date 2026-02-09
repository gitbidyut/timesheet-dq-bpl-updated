import os
import sys
import json
import pandas as pd

# ==============================
# SageMaker standard paths
# ==============================
INPUT_DIR = "/opt/ml/processing/input"
OUTPUT_DIR = "/opt/ml/processing/output"

INPUT_FILE = os.path.join(INPUT_DIR, "timesheet.csv")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "dq_result.json")

print("🔍 Starting Data Quality Check")
print(f"📂 Input file expected at: {INPUT_FILE}")
print(f"📂 Output will be written to: {OUTPUT_FILE}")

# ==============================
# Helper functions
# ==============================
def fail_pipeline(errors):
    """Write FAIL result and exit with error"""
    result = {
        "status": "FAIL",
        "errors": errors
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print("❌ DATA QUALITY CHECK FAILED")
    for e in errors:
        print(f" - {e}")

    sys.exit(1)


def pass_pipeline():
    """Write PASS result and exit cleanly"""
    result = {
        "status": "PASS",
        "errors": []
    }
    with open(OUTPUT_FILE, "w") as f:
        json.dump(result, f, indent=2)

    print("✅ DATA QUALITY CHECK PASSED")
    sys.exit(0)


# ==============================
# Step 1: Check input file
# ==============================
if not os.path.exists(INPUT_FILE):
    fail_pipeline([f"Input file not found: {INPUT_FILE}"])

# ==============================
# Step 2: Load CSV
# ==============================
try:
    df = pd.read_csv(INPUT_FILE)
    print(f"📊 Loaded data with {len(df)} rows and {len(df.columns)} columns")
except Exception as e:
    fail_pipeline([f"Failed to read CSV: {str(e)}"])

errors = []

# ==============================
# Step 3: Required columns check
# ==============================
required_columns = [
    "Employee",
    "Employee Nr.",
    "Cost Center",
    "Activity Code",
    "Date",
    "Hours"
]

for col in required_columns:
    if col not in df.columns:
        errors.append(f"Missing required column: {col}")

if errors:
    fail_pipeline(errors)

# ==============================
# Step 4: Null / blank checks
# ==============================
null_threshold = 0.10  # 10%

null_ratio = df["Activity Code"].isna().mean()
if null_ratio > null_threshold:
    errors.append(
        f"Too many NULL values in Activity Code: {null_ratio:.2%}"
    )

# ==============================
# Step 5: Leading / trailing spaces
# ==============================
string_columns = ["Description", "Activity Code"]

for col in string_columns:
    if col in df.columns:
        bad_spaces = df[col].astype(str).str.match(r"^\s+|\s+$").any()
        if bad_spaces:
            errors.append(f"Leading/trailing spaces detected in column: {col}")

# ==============================
# Step 6: Business rule checks
# ==============================
if (df["Hours"] < 0).any():
    errors.append("Negative hours detected")

if (df["Hours"] > 24).any():
    errors.append("Hours greater than 24 detected")

# ==============================
# Step 7: Final decision
# ==============================
if errors:
    fail_pipeline(errors)
else:
    pass_pipeline()
