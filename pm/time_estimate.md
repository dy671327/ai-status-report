# Time estimate: one weekly status report

**This is an estimate, not a stopwatch measurement.** Each step is timed from published reading and writing speeds and this project's real sizes. Steps marked *assumption* use a stated figure that can be checked by timing it.

## Inputs

| Input | Value | Source |
|---|---|---|
| Composing speed at a keyboard | 19 words per minute | Karat et al. (1999), average computer users composing text |
| Silent reading speed, non-fiction | 238 words per minute | Brysbaert (2019), meta-analysis of 190 studies |
| Report length | 182 words | Average of reports 1 to 3 |
| Claims to verify | 27 | Average claims checked in the 3 final reports (`report_checks.csv`) |
| Open issues | 23 | Sample sprint, 16 Oct |
| Scan one row in a sorted sheet | 5 s | Assumption |
| Work out days late or days since update | 30 s per issue | Assumption |
| Verify one claim against the source | 10 s | Assumption, same rate for both methods |

## Manual: about 25 minutes

| Step | Minutes | Basis |
|---|---|---|
| Open export, filter out Done, count done/open/total | 2.0 | Assumption |
| Overdue: sort by Due Date, scan, work out days late | 3.9 | 23 rows x 5 s + 4 x 30 s |
| Stale: sort by Updated, scan, work out days since update | 3.4 | 23 rows x 5 s + 3 x 30 s |
| Unassigned high priority: filter | 1.0 | Assumption |
| Write the report | 9.6 | 182 words at 19 wpm |
| Read it through once | 0.8 | 182 words at 238 wpm |
| Check every claim against the sheet | 4.6 | 27 claims x 10 s |
| **Total** | **25.2** | |

## With the MVP: about 7 minutes

| Step | Minutes | Basis |
|---|---|---|
| Run `mvp.py` | 0.5 | Typing the command; the script itself was measured at under 1 second (`timings.csv`) |
| Paste facts.json into Claude and get the report | 1.0 | Assumption |
| Read it through once | 0.8 | 182 words at 238 wpm |
| Check every claim against facts.json | 4.6 | 27 claims x 10 s |
| Save the report | 0.5 | Assumption |
| **Total** | **7.3** | |

## Result

Estimated saving: **17.9 minutes per report (71%)**. Most of the saving comes from not writing the report by hand (9.6 minutes) and not working out the risks row by row (8.3 minutes). The review step is kept in full, so the MVP estimate does not assume the AI output is trusted without checking.

## Sources

- Karat, C.-M., Halverson, C., Horn, D. and Karat, J. (1999). *Patterns of entry and correction in large vocabulary continuous speech recognition systems.* CHI '99. Figures as summarised at https://en.wikipedia.org/wiki/Words_per_minute
- Brysbaert, M. (2019). *How many words do we read per minute? A review and meta-analysis of reading rate.* Journal of Memory and Language, 109. https://www.Gwern.net/doc/psychology/linguistics/2019-brysbaert.pdf
