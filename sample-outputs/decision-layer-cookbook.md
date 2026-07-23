# Expected Output — Decision Layer Cookbook

Captured from the executed OFFLINE notebook (`notebooks/01_decision_layer_cookbook.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
state: answered  effective: mask_partial
{
  "domain": "Customer Data",
  "owner": "Revenue Operations",
  "purpose": "Customer master data used for approved reporting, analytics, support, and controlled operational exports.",
  "steward": "privacy-review@example.com"
}
```

```text
{
  "classification": {
    "category": "pii",
    "sensitivity": "restricted",
    "subcategory": null
  },
  "data_type": "text",
  "masking": {
    "exempt_roles": [
      "DATA_STEWARD",
      "PRIVACY_ADMIN"
    ],
    "type": "partial"
  },
  "meaning": "Primary contact email address for the customer.",
  "pii": true,
  "ref": {
    "column": "email",
    "database": "acmecloud_demo",
    "schema": "public",
    "table": "customers"
  }
}
```

```text
state: answered  active rules: 18
```

```text
transfer decision: conditional (residency.cross_border_transfer)
{
  "defaultEffect": "conditional",
  "rules": [
    {
      "consumerJurisdictions": [
        "EU"
      ],
      "destinationJurisdictions": [
        "US"
      ],
      "destinationSystems": [
        "SALESFORCE"
      ],
      "effect": "conditional",
      "operations": [
        "export"
      ],
      "requiredRole": "PRIVACY_ADMIN",
      "requiresAnonymization": true,
      "requiresApproval": true
    },
    {
      "destinationSystems": [
        "ADS_PLATFORM"
      ],
      "effect": "deny"
    },
    {
      "destinationSystems": [
        "EXTERNAL_LLM_VENDOR"
      ],
      "effect": "deny"
    }
  ]
}
```

```text
state:    answered
decision: allow
reason:   acme-customer-use v1 usage_guidance:spec.usage.permittedUses:permitted → allow on acmecloud_demo.public.customers
can_proceed_now: True
```

```text
state:    answered
decision: deny
reason:   acme-customer-use v1 usage_guidance:spec.usage.prohibitedUses:prohibited → deny on acmecloud_demo.public.customers
prohibition: acme-customer-use v1 usage_guidance:spec.usage.prohibitedUses:prohibited → deny on acmecloud_demo.public.customers
can_proceed_now: False
```

```text
aggregate query -> pass
detail query    -> warn (a masked column is referenced)
  mask_partial: acme-email-masking v1 masking:spec.accessControl.masking → mask_partial on acmecloud_demo.public.customers.email
  allow: acme-customer-use v1 usage_guidance:spec.usage.permittedUses:permitted → allow on acmecloud_demo.public.customers
```

```text
current: True
Decision 'allow' on acmecloud_demo.public.customers was produced by policy 'AcmeCloud customer use guardrails' v1 (instruction 'usage_guidance:spec.usage.permittedUses:permitted', scenario 'purpose.allowed_use', current publication): acme-customer-use v1 usage_guidance:spec.usage.permittedUses:permitted → allow on acmecloud_demo.public.customers
{
  "policy_id": "accef000-0000-4000-8000-000000000006",
  "policy_name": "AcmeCloud customer use guardrails",
  "policy_version_id": "accef000-0000-4000-8000-000000000007",
  "version_number": 1
}
```
