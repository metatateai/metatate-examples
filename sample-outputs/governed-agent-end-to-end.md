# Expected Output — The Governed Agent, End To End

Captured from the executed OFFLINE notebook (`notebooks/14_governed_agent_end_to_end.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
rulebook: 18 active rules on customers (ai_governance, business_context, classification, lineage, masking, ...)
dashboard use -> allow
draft SQL: SELECT customer_name, email FROM customers WHERE region = 'EU'
validate -> warn
revised SQL: SELECT region, SUM(arr) FROM customers GROUP BY region
validate -> pass
dashboard SQL accepted after governance review
Salesforce export -> conditional
exception packet exception-arc-export-salesforce -> pending_human_review (queue: privacy-review)
review approved with attested controls -> resumed_with_controls
fine-tune on raw tickets -> deny
reroute: train on ml_feature_store features -> allow
explain_why chained over 4 decisions (all current: True)
```

```text
 1. inspect_governance_rules -> answered
 2. authorize_use            -> allow
 3. validate_query_context   -> warn
 4. validate_query_context   -> pass
 5. authorize_use            -> conditional
 6. authorize_use            -> deny
 7. authorize_use            -> allow
 8. explain_why              -> current
 9. explain_why              -> current
10. explain_why              -> current
11. explain_why              -> current
```

```text
draft:   SELECT customer_name, email FROM customers WHERE region = 'EU'
final:   SELECT region, SUM(arr) FROM customers GROUP BY region
revisions: 1 (dashboard validated)
```

```text
packet:  exception-arc-export-salesforce -> queue privacy-review
attestations required: ['approval_recorded', 'anonymization_before_transfer']
status:  resumed_with_controls
resume:  resume_controlled_workflow
```

```text
training: rerouted_to_governed_alternative (rerouted: True)
```

```text
accef000-0000-4000-8000-000000000020 -> current: True
accef000-0000-4000-8000-000000000010 -> current: True
accef000-0000-4000-8000-000000000043 -> current: True
accef000-0000-4000-8000-000000000064 -> current: True
total Metatate calls: 11
```
