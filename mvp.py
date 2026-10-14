# mvp.py - flags risks in a Jira CSV export and saves them to facts.json
# Run:  python mvp.py data\sample_jira.csv 2026-10-16

import sys
import json
import pandas as pd

# ---- 1. Settings ----
# The CSV path and report date come from the command line. If they're missing,
# fall back to the sample data and today's date.
CSV_PATH = sys.argv[1] if len(sys.argv) > 1 else "data/sample_jira.csv"
REPORT_DATE = pd.Timestamp(sys.argv[2]) if len(sys.argv) > 2 else pd.Timestamp.today().normalize()

STALE_DAYS = 7                                    # no update for this many days = stale
HIGH_PRIORITIES = ["High", "Highest"]             # priorities that must have an owner
DONE_STATUSES = ["Done", "Closed", "Resolved"]    # everything else counts as open
FACTS_PATH = "facts.json"
ANSWER_KEY_PATH = "data/answer_key.csv"

# ---- 2. Load and clean ----
# Turn date text into real dates so they can be compared. Bad or blank dates become NaT (empty).
df = pd.read_csv(CSV_PATH)
for col in ["Created", "Updated", "Due Date", "Resolved"]:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")

# Blank assignees are read as NaN; turn them into "" so the check is a simple == "".
df["Assignee"] = df["Assignee"].fillna("").astype(str).str.strip()
df["Status"] = df["Status"].astype(str).str.strip()

# True for every issue that is not finished. ~ means "not".
is_open = ~df["Status"].isin(DONE_STATUSES)

# ---- 3. The three rules ----
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

# ---- 4. Print and save ----
# Show a summary line and a table, then write the facts Claude will use in Session 4.
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

# ---- 5. Check against the answer key (only if it exists) ----
# Recall = how many planted risks we caught. Precision = how many of our flags were right.
try:
    key = pd.read_csv(ANSWER_KEY_PATH)
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
    print(f"\nNo {ANSWER_KEY_PATH} found, skipping the accuracy check.")
