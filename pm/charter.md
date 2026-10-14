# Project Charter: AI Status Report Generator (MVP)

**Problem:** Weekly status reports take [X] minutes to write by hand (baseline to be measured in Session 2), and risks buried in Jira get missed.

**Goal:** A script that flags risks from a Jira CSV, plus a Claude prompt that writes the report.

**In scope:** 3 risk rules (overdue, stale, unassigned high priority), synthetic test data, Claude Project prompt, timing test.

**Out of scope:** Web app, Claude API, real company data, meeting notes.

**Success criteria:**
- Catches 10 of 10 planted risks
- Zero invented facts in 3 reports
- Time measured before and after

**Deadline:** 2026-10-28

**Owner:** Deepak Yadav
