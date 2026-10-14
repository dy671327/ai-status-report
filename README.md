# AI Status Report Generator (MVP)

Turns a Jira CSV export into a weekly status report. Python rules find the risks; Claude writes the report from those facts only.

**[View the project dashboard →](https://dy671327.github.io/ai-status-report/)**

## The problem

Weekly status reports take time to write by hand, and risks buried in Jira get missed: an overdue ticket, an issue nobody has updated in a week, or a high-priority item with no owner.

## Results (MVP, synthetic data)

| Measure | Result |
|---|---|
| Risk detection | Caught **10 of 10** planted risks, **0 extra flags** (recall 100%, precision 100%) on the 16 Oct test date |
| Report accuracy | Report 1 checked line by line: 3 invented facts in the first draft, **0 in the final draft** (22 claims checked). Reports 2 and 3 in progress |
| Time saved | Not yet measured (manual vs MVP timing planned) |

## How it works

```
Jira CSV  ──►  mvp.py  ──►  facts.json  ──►  Claude Project  ──►  status report  ──►  line-by-line check
             (3 rules)     (only input        (fixed prompt)
                            Claude sees)
```

1. **`mvp.py` checks the input** (see [Input validation](#input-validation-for-real-jira-data) below), then **applies 3 rules** to open issues. Jira's Status Category decides what is finished when the export has it; otherwise Done, Closed and Resolved count as finished:

   | Rule | Flags an issue when |
   |---|---|
   | Overdue | Due date is before the report date |
   | Stale | Last update was 7 or more days before the report date |
   | Unassigned high priority | Priority is High or Highest and Assignee is blank |

2. **Saves `facts.json`**: report date, issue counts, and each risk with its issue key and a one-line reason.
3. **A Claude Project with fixed instructions** (`prompt.md`) writes the report: summary, RAG status, progress, top risks with issue keys, and decisions needed.
4. **Every report is checked line by line** against `facts.json`. Results are logged in `pm/report_checks.csv`.

### Why split the work between Python and Claude?

Python is reliable at checking rules but bad at writing. Claude is good at writing but can invent things. So Python decides what the risks are, and Claude only explains them.

### How invented facts are prevented

- **Limit what the AI sees.** Claude gets only `facts.json`, never the raw CSV. It contains no names, so any name in a report is an invented fact.
- **Turn judgement into rules.** The RAG colour (Red if 8 or more risks, Amber 3 to 7, Green 0 to 2), the order of the top 5 risks, and what is forbidden (causes, names, new numbers) are fixed in the prompt.
- **Check every line.** Each issue key, number and reason is compared with `facts.json` before a report counts as done.

## Run it

Requires Python 3.12 or newer.

```
pip install pandas openpyxl
python mvp.py data/sample_jira.csv 2026-10-16
```

The two inputs are the path to a Jira export (`.csv` or `.xlsx`) and the report date (`YYYY-MM-DD`). `openpyxl` is only needed for `.xlsx` files. A fixed report date gives the same answer every run, so tests can be repeated. If `data/answer_key.csv` exists, the script also prints recall, precision, and any missed or extra issues.

Expected output starts with the input checks and ends with the accuracy check:

```
Input checks: 40 issues read from sample_jira.csv
  Finished when: Status is Done, Closed, Resolved
  Treated as open: In Progress, In Review, To Do
  No warnings
...
Caught 10 of 10 planted risks (recall 100%); 0 extra flags (precision 100%)
```

## Input validation for real Jira data

A first test on a real Jira export (one issue, `.xlsx`, custom workflow) broke the original pipeline: it crashed on the Excel file, crashed on a column named `Due date` instead of `Due Date`, and flagged a finished issue as Stale because its custom status (`Pending PO Verification`) wasn't in the Done list. The script now checks the input before any rule runs.

| Check | Result |
|---|---|
| File exists, is `.csv` or `.xlsx`, and has issue rows | Stop with a clear message |
| Report date is a real date | Stop |
| Required columns present (Issue key, Status, Priority, Assignee, Updated, Due Date) | Stop, listing the columns found |
| Column names matched regardless of capitals and spaces | Auto-fix |
| Rows without an issue key | Warning, row skipped |
| Duplicate issue keys | Warning |
| Dates that can't be read | Warning, with example keys |
| Issues updated after the report date | Warning (likely a wrong report date) |
| Done vs open decided by Jira's Status Category when present | Auto-fix |
| Statuses treated as open | Printed, so the PM can spot a finished status counted as open |
| CSV encoding (UTF-8, then Windows) | Auto-fix |
| Answer-key accuracy check | Only runs when the key matches the data |

Tested on 8 inputs: the sample data (still 10 of 10, 0 extra flags), the real export (read directly, 0 risks), a messy CSV (all 4 warnings raised), and five broken inputs that each stopped with a clear message.

## Test data

[`data/sample_jira.csv`](data/sample_jira.csv) is a synthetic Jira export: 40 issues (ONB-101 to ONB-140) for one 2-week sprint (5 to 16 Oct 2026) of a 5-person team building a customer onboarding portal. Ten risks were planted on purpose (4 overdue, 3 stale, 3 unassigned high priority) and listed in [`data/answer_key.csv`](data/answer_key.csv), so the script can be scored.

## Repository structure

| Path | Contents |
|---|---|
| [`mvp.py`](mvp.py) | The risk script |
| [`facts.json`](facts.json) | Output of the latest run |
| [`data/`](data/) | Synthetic Jira export and answer key |
| `prompt.md` | Claude Project instructions |
| `reports/` | Generated reports and the facts each one was based on |
| [`pm/`](pm/) | Charter and report checks |
| [`docs/`](docs/) | Project dashboard (GitHub Pages) |

## Limitations

- Risk accuracy measured on synthetic data; real-data testing so far is one single-issue export (not included in the repo)
- 3 rules: overdue, stale, unassigned high priority
- Out of scope for the MVP: web app, Claude API, meeting notes
- Still to do: reports 2 and 3, a test on a fresh unseen dataset, and before/after timing

## Project management

The project charter is in [`pm/charter.md`](pm/charter.md). Report checks, timings and lessons learned are kept in `/pm`. Built by Deepak Yadav with help from Claude.
