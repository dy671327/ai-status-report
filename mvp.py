# mvp.py - flags risks in a Jira export (CSV or Excel) and saves them to facts.json
# Run:  python mvp.py data\sample_jira.csv 2026-10-16

import os
import sys
import json
import pandas as pd


def stop(message):
    """Print a clear input error and end the script, instead of a Python crash."""
    print(f"\nINPUT ERROR: {message}")
    sys.exit(1)


# ---- 1. Settings ----
# The file path and report date come from the command line. If they're missing,
# fall back to the sample data and today's date.
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/sample_jira.csv"
try:
    REPORT_DATE = pd.Timestamp(sys.argv[2]) if len(sys.argv) > 2 else pd.Timestamp.today().normalize()
except ValueError:
    stop(f"Report date '{sys.argv[2]}' is not a date. Use YYYY-MM-DD, e.g. 2026-10-16")

STALE_DAYS = 7                                    # no update for this many days = stale
HIGH_PRIORITIES = ["High", "Highest"]             # priorities that must have an owner
DONE_STATUSES = ["Done", "Closed", "Resolved"]    # used only if there is no Status Category column
REQUIRED_COLUMNS = ["Issue key", "Status", "Priority", "Assignee", "Updated", "Due Date"]
OPTIONAL_COLUMNS = ["Summary", "Created", "Resolved", "Status Category"]
DATE_COLUMNS = ["Created", "Updated", "Due Date", "Resolved"]
FACTS_PATH = "facts.json"
ANSWER_KEY_PATH = "data/answer_key.csv"

# ---- 2. Load the file ----
# Jira can export CSV or Excel (.xlsx). Anything else is stopped with a clear message.
if not os.path.exists(CSV_PATH):
    stop(f"File not found: {CSV_PATH}")

extension = os.path.splitext(CSV_PATH)[1].lower()
if extension == ".csv":
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(CSV_PATH, encoding="cp1252")   # older Excel "Save as CSV" files
elif extension == ".xlsx":
    try:
        df = pd.read_excel(CSV_PATH, sheet_name=0)      # Jira puts the issue fields on the first sheet
    except ImportError:
        stop("Reading .xlsx files needs openpyxl. Run: pip install openpyxl")
else:
    stop(f"'{extension}' files are not supported. Export from Jira as .csv or .xlsx")

if df.empty:
    stop("The file has no issue rows.")

# ---- 3. Validate the input ----
# Real exports differ from the test data, so check the input before trusting any risk.
# Problems that make the result wrong stop the script; smaller ones are listed as warnings.
warnings = []

# Column names: match regardless of capitals and spaces, so "Due date" works as "Due Date".
lookup = {str(col).strip().lower(): col for col in df.columns}
renames = {}
for wanted in REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
    found = lookup.get(wanted.lower())
    if found is not None and found != wanted:
        renames[found] = wanted
df = df.rename(columns=renames)

missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
if missing:
    stop(f"Missing column(s): {', '.join(missing)}. "
         f"Columns found: {', '.join(str(c) for c in df.columns[:15])}")

# Issue keys: every risk must point to a real issue, so rows without a key are dropped.
no_key = df["Issue key"].isna() | (df["Issue key"].astype(str).str.strip() == "")
if no_key.any():
    warnings.append(f"{no_key.sum()} row(s) without an Issue key were skipped")
    df = df[~no_key]
duplicates = df.loc[df["Issue key"].duplicated(), "Issue key"].unique()
if len(duplicates) > 0:
    warnings.append(f"Duplicate issue keys: {', '.join(map(str, duplicates))}")

# Dates: turn text into real dates. Text that can't be read becomes empty (NaT) and is reported,
# because an unreadable due date would silently hide an overdue issue.
for col in DATE_COLUMNS:
    if col in df.columns:
        raw = df[col]
        df[col] = pd.to_datetime(raw, errors="coerce")
        unreadable = raw.notna() & (raw.astype(str).str.strip() != "") & df[col].isna()
        if unreadable.any():
            keys = ", ".join(df.loc[unreadable, "Issue key"].astype(str).head(5))
            warnings.append(f"{unreadable.sum()} '{col}' value(s) could not be read as dates (e.g. {keys})")

future = df["Updated"] > REPORT_DATE + pd.Timedelta(days=1)
if future.any():
    warnings.append(f"{future.sum()} issue(s) updated after the report date - is the report date right?")

# Blank assignees are read as NaN; turn them into "" so the check is a simple == "".
df["Assignee"] = df["Assignee"].fillna("").astype(str).str.strip()
df["Status"] = df["Status"].astype(str).str.strip()
df["Priority"] = df["Priority"].fillna("").astype(str).str.strip()

# Done or open: real Jira workflows use custom statuses (e.g. "Pending PO Verification"),
# so use Jira's own Status Category when the export has it. Otherwise use DONE_STATUSES.
if "Status Category" in df.columns:
    done_rule = "Status Category is Done"
    is_open = df["Status Category"].astype(str).str.strip() != "Done"
else:
    done_rule = "Status is " + ", ".join(DONE_STATUSES)
    is_open = ~df["Status"].isin(DONE_STATUSES)   # ~ means "not"

open_statuses = sorted(df.loc[is_open, "Status"].unique())
print(f"\nInput checks: {len(df)} issues read from {os.path.basename(CSV_PATH)}")
print(f"  Finished when: {done_rule}")
print(f"  Treated as open: {', '.join(open_statuses) if open_statuses else 'none'}")
for w in warnings:
    print("  WARNING:", w)
if not warnings:
    print("  No warnings")

# ---- 4. The three rules ----
# Each rule filters the open issues, then adds one row per match to the risks list.
risks = []

# Rule 1: Overdue - due date is before the report date
overdue = df[is_open & (df["Due Date"] < REPORT_DATE)]
for _, row in overdue.iterrows():
    days_late = (REPORT_DATE - row["Due Date"]).days
    risks.append({
        "issue": row["Issue key"],
        "rule": "Overdue",
        "reason": f"Due {row['Due Date'].date()}, {days_late} days late, status {row['Status']}",
    })

# Rule 2: Stale - last update was STALE_DAYS or more days before the report date
days_since_update = (REPORT_DATE - df["Updated"]).dt.days
stale = df[is_open & (days_since_update >= STALE_DAYS)]
for _, row in stale.iterrows():
    days_quiet = (REPORT_DATE - row["Updated"]).days
    risks.append({
        "issue": row["Issue key"],
        "rule": "Stale",
        "reason": f"No update for {days_quiet} days (last {row['Updated'].date()})",
    })

# Rule 3: Unassigned high priority - High or Highest with nobody assigned
unassigned = df[is_open & df["Priority"].isin(HIGH_PRIORITIES) & (df["Assignee"] == "")]
for _, row in unassigned.iterrows():
    risks.append({
        "issue": row["Issue key"],
        "rule": "Unassigned high priority",
        "reason": f"{row['Priority']} priority with no assignee",
    })

# ---- 5. Print and save ----
# Show a summary line and a table, then write the facts Claude will use to write the report.
risk_df = pd.DataFrame(risks, columns=["issue", "rule", "reason"])

print(f"\nReport date: {REPORT_DATE.date()}  |  Issues: {len(df)}  |  "
      f"Done: {(~is_open).sum()}  |  Open: {is_open.sum()}  |  Risks: {len(risk_df)}\n")
if risk_df.empty:
    print("No risks found.")
else:
    print(risk_df.to_string(index=False))

facts = {
    "report_date": str(REPORT_DATE.date()),
    "total_issues": int(len(df)),
    "done": int((~is_open).sum()),
    "open": int(is_open.sum()),
    "risk_counts": {rule: int(n) for rule, n in risk_df["rule"].value_counts().items()},
    "risks": risks,
}
with open(FACTS_PATH, "w", encoding="utf-8") as f:
    json.dump(facts, f, indent=2)
print(f"\nSaved {FACTS_PATH}")

# ---- 6. Check against the answer key (only if it exists) ----
# Recall = how many planted risks we caught. Precision = how many of our flags were right.
try:
    key = pd.read_csv(ANSWER_KEY_PATH)
    # The key only applies to the dataset it was written for (e.g. not to a real export).
    if not set(key["Issue key"]) & set(df["Issue key"]):
        raise FileNotFoundError
    expected = set(zip(key["Issue key"], key["Rule"]))
    found = set(zip(risk_df["issue"], risk_df["rule"]))
    caught = len(expected & found)
    print(f"\nCaught {caught} of {len(expected)} planted risks "
          f"(recall {caught / len(expected):.0%}); "
          f"{len(found - expected)} extra flags (precision {caught / max(len(found), 1):.0%})")
    for miss in sorted(expected - found):
        print("  MISSED:", miss)
    for extra in sorted(found - expected):
        print("  EXTRA: ", extra)
except FileNotFoundError:
    print("\nNo answer key for this data, skipping the accuracy check.")
