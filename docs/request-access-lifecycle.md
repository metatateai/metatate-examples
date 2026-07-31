# Server-backed access request lifecycle

Metatate Cloud exposes nine MCP tools. The default examples pack safely replays
seven; `request_access` and `check_request` are demonstrated here because the
first creates real workflow state and can notify configured stewards.

Preview the exact flow without calling an endpoint:

```bash
python3 -m request_lifecycle.cli
```

To run it against your workspace, load the AcmeCloud demo and create a token
with both `read` and `request` scopes. Then export the normal live-mode
variables and run:

```bash
python3 -m request_lifecycle.cli --live-submit --tenant-slug <workspace-slug>
```

The CLI refuses non-interactive submission. It first asks before recording the
cited authorization, then prints the exact `request_access` source and requires
a second confirmation bound to that server-minted `authorization_id`. It does
not send a note by default.

The returned request is real. Complete it in **Activity → Review requests**.
Read its status later with the same subject token:

```bash
python3 -m request_lifecycle.cli --request-id <request-id>
```

After a steward grants an active exception, retry the canonical authorization:

```bash
python3 -m request_lifecycle.cli --request-id <request-id> --retry
```

The retry supplies `satisfied_conditions: [{kind: "approval", exception_id}]`.
The server verifies subject, liveness, and scope; the caller never asserts that
the condition is satisfied. A revoked or expired grant is refused.

This workflow is intentionally absent from automated live CI. The repository's
shared release credential is read-only, and an automated `request_access` would
create a real open request without a confirming user. The AcmeCloud demo's
Activity records come from the product's authoritative database fixture, not
from the MCP response recordings in this repository.
