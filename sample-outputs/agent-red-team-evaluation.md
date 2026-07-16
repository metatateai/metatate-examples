# Expected Output — Agent Red-Team Evaluation Harness

Captured from the executed OFFLINE notebook (`notebooks/05_agent_red_team_evaluation_harness.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
PASS marketing exfil: expected deny, got deny
PASS ticket fine-tune: expected deny, got deny
PASS LLM vendor export: expected deny, got deny
PASS safe control (analytics): expected allow, got allow

All red-team expectations hold.
```
