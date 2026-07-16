# Expected Output — OpenAI Agents SDK Tool Guard Pattern

Captured from the executed OFFLINE notebook (`notebooks/08_openai_agents_tool_guard_pattern.ipynb`), which replays
recorded Metatate Cloud answers — live mode against a workspace serving the
AcmeCloud demo publication produces the same decisions.


```text
{'executed': True, 'decision': 'allow', 'evidence': 'accef000-0000-4000-8000-000000000020'}
{'executed': False, 'decision': 'deny', 'reason': 'acme-customer-use v1 usage_guidance:spec.usage.prohibitedUses:prohibited → deny on acmecloud_demo.public.customers'}
```
