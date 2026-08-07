# Expected Output — Purpose-Bound Agent Data Windows

Captured from the executed offline notebook
(`notebooks/16_purpose_bound_agent_data_windows.ipynb`). Offline mode replays
native Metatate Cloud responses recorded from the Customer 360 sample
publication; it does not use the legacy Snowflake response envelope.

The first four calls show the policy matrix. Database and purpose select the
window type and duration; the server supplies the rolling anchor, while the
caller must supply the date-of anchor.

```text
master / research      -> conditional  rolling 90 days
master / commercial    -> conditional  rolling 30 days
product / research     -> conditional  as_of   90 days
product / commercial   -> conditional  as_of   30 days
```

Missing decision-bearing context fails closed. A declared purpose is required
for both databases, and the product database also requires an explicit
`data_access_context.as_of` timestamp.

```text
missing purpose -> review_required access_window_context_required
missing as_of   -> review_required access_window_context_required
```

`validate_query_context` then proves the SQL respects the exact time bound.
The four policy-compliant queries pass:

```text
master research 90       -> pass / answered
master commercial 30     -> pass / answered
product research 90      -> pass / answered
product commercial 30    -> pass / answered
```

The two deliberately broader windows fail. A 90-day query cannot satisfy a
30-day commercial grant, regardless of whether the policy uses a rolling or
date-of anchor.

```text
commercial rolling 90 -> fail
commercial as-of 90   -> fail
```

This is a proof boundary, not advisory prose: an agent receives the window in
the authorization response and must still present SQL whose predicate proves
that it stayed inside the window.
