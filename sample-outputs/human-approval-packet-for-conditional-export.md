# Expected Output — Human Approval Packet For Conditional Export

Captured from the executed OFFLINE notebook (`notebooks/09_human_approval_packet_for_conditional_export.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
Human-in-the-loop exception workflow
  ready_without_exception: 1
  resumed_with_controls: 1
  pending_review: 0
  requires_changes: 0
  rejected_by_reviewer: 0
  blocked_by_policy: 1
  needs_policy_review: 0

req-001: ready_without_exception (pass) evidence=accef000-0000-4000-8000-000000000001
req-002: resumed_with_controls (conditional) evidence=accef000-0000-4000-8000-000000000010
  queue: privacy-review
  rationale: Transfer to SALESFORCE (US) for consumer jurisdiction EU requires approval and anonymization and role PRIVACY_ADMIN (policy AcmeCloud transfer guardrails).
  reviewer: privacy-review@example.com -> approve
  resume: resume_controlled_workflow
req-003: blocked_by_policy (deny) evidence=accef000-0000-4000-8000-000000000028
  rationale: acme-customer-use v1 ai_governance:spec.aiGovernance:training → deny on acmecloud_demo.public.support_tickets
```

```text
{
  "packet_id": "exception-req-002",
  "request_id": "req-002",
  "title": "Export customer fields to Salesforce",
  "description": "Sync customer fields to Salesforce for account operations.",
  "owner": "Revenue Operations",
  "decision": "conditional",
  "evidence_id": "accef000-0000-4000-8000-000000000010",
  "source": "acmecloud_demo.public.customers",
  "destination": {
    "system": "SALESFORCE",
    "jurisdiction": "US"
  },
  "consumer_jurisdiction": "EU",
  "required_controls": [
    "This data must be anonymized before the transfer.",
    "Transfer to SALESFORCE (US) for consumer jurisdiction EU requires approval and anonymization and role PRIVACY_ADMIN (policy AcmeCloud transfer guardrails)."
  ],
  "required_attestations": [
    "approval_recorded",
    "anonymization_before_transfer"
  ],
  "obligations": [],
  "rationale": "Transfer to SALESFORCE (US) for consumer jurisdiction EU requires approval and anonymization and role PRIVACY_ADMIN (policy AcmeCloud transfer guardrails).",
  "reviewer_note": "You may proceed only after satisfying the stated condition(s) below (e.g. obtain the named approval, anonymize first, or act as a granted role).",
  "reviewer_queue": "privacy-review",
  "policy_response_state": "answered"
}
```
