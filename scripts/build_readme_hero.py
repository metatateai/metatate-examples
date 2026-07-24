#!/usr/bin/env python3
"""Generate docs/assets/readme-hero.svg — the animated README terminal.

The hero is a GENERATED artifact, exactly like the notebooks: the storyboard
below quotes the governed-agent-arc's recorded answers (notebook 14 /
governed_agent_arc), each beat citing the fixture case it compresses, and CI
fails on drift via ``--check`` (wired into scripts/validate_examples.py).
Edit the STORYBOARD, rerun this script, commit both files.
"""

from __future__ import annotations

import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "docs" / "assets" / "readme-hero.svg"

WIDTH = 880
DUR = 24.0  # seconds per loop
HOLD = 0.8438  # every line holds until here...
FADE = 0.8750  # ...and has faded by here (same scheme as the previous hero)
REVEAL_START = 0.03
REVEAL_STEP = 0.045
EPSILON = 0.15 / DUR  # ~150ms ramp, matching the original hand-authored feel

BG = "#0A1628"
CHROME = "#0F1E32"
RULE = "#22314a"
GREEN = "#C3FFB2"
RED = "#FF6B5B"
AMBER = "#FBBF24"
TEAL = "#4ECDC4"
CODE = "#c9d1d9"
MUTED = "#8b949e"
FOOT = "#6e7681"

ARIA = (
    "Animated terminal: one agent brief runs end to end against Metatate — the "
    "rulebook is read first, a warned SQL draft is revised to a passing "
    "aggregate, a Salesforce export is conditional and resumes only with "
    "attested controls, a fine-tune on raw tickets is denied and rerouted to "
    "the governed feature store, and explain_why confirms every decision is "
    "current."
)
DESC = (
    "A Python session against the AcmeCloud demo domain running the governed "
    "agent arc (notebook 14). inspect_governance_rules returns 18 active "
    "rules. validate_query_context returns WARN for a masked-column draft, "
    "then PASS for the revised aggregate (fixtures email-detail-warn and "
    "safe-aggregate-pass). authorize_use for a Salesforce export returns "
    "CONDITIONAL with approval_required and anonymize_first "
    "(export-salesforce-conditional); the exception packet resumes with "
    "attested controls. authorize_use for fine-tuning on support tickets "
    "returns DENY (train-support-tickets-deny) and the reroute to "
    "ml_feature_store returns ALLOW (ml-training-features-allow). explain_why "
    "reports every decision current."
)

# One storyboard line = (gap_before_px, [spans]); span = (color, text, bold).
# fill=BG spans are the invisible alignment prefix trick from the original.
P = [(GREEN, ">>> ", False)]  # prompt prefix
H = [(BG, ">>> ", False)]  # hidden continuation prefix

STORYBOARD: list[tuple[int, list[tuple[str, str, bool]]]] = [
    # Beat 0 — read the rulebook first (fixture: rules_customers).
    (0, P + [(CODE, 'client.inspect_governance_rules(asset(', False), (TEAL, '"customers"', False), (CODE, "))", False)]),
    (26, [(TEAL, "☰ 18 RULES", True), (MUTED, "  masking · ai.training deny · destination-aware transfers — read BEFORE acting", False)]),
    # Beat 1 — the draft that had to change (email-detail-warn → safe-aggregate-pass).
    (36, P + [(CODE, "client.validate_query_context(", False), (TEAL, '"SELECT customer_name, email FROM customers …"', False), (CODE, ")", False)]),
    (26, [(AMBER, "◐ WARN", True), (MUTED, "  masked column referenced — the agent revises, it does not argue", False)]),
    (22, [(GREEN, "✓ PASS", True), (MUTED, "  SELECT region, SUM(arr) FROM customers GROUP BY region", False)]),
    # Beat 2 — conditional export → packet → resumed (export-salesforce-conditional).
    (36, P + [(CODE, "client.authorize_use(asset(", False), (TEAL, '"customers"', False), (CODE, "), use=", False), (TEAL, '"sync approved customer fields to the CRM"', False), (CODE, ",", False)]),
    (22, H + [(CODE, "    operation=", False), (TEAL, '"export"', False), (CODE, ", destination={", False), (TEAL, '"system"', False), (CODE, ": ", False), (TEAL, '"SALESFORCE"', False), (CODE, "}, consumer_jurisdiction=", False), (TEAL, '"EU"', False), (CODE, ")", False)]),
    (26, [(AMBER, "◐ CONDITIONAL", True), (MUTED, "  approval_required · anonymize_first → exception packet → RESUMED with attested controls", False)]),
    # Beat 3 — deny becomes redirection (train-support-tickets-deny → ml-training-features-allow).
    (36, P + [(CODE, "client.authorize_use(asset(", False), (TEAL, '"support_tickets"', False), (CODE, "), use=", False), (TEAL, '"fine-tune a support assistant on ticket text"', False), (CODE, ")", False)]),
    (26, [(RED, "✗ DENY", True), (MUTED, "  ai.training prohibited on raw tickets — the agent reroutes, it does not work around", False)]),
    (22, [(GREEN, "✓ ALLOW", True), (MUTED, "  ai.training on ml_feature_store features — the estate's sanctioned path", False)]),
    # Beat 4 — the receipts (explain chains).
    (36, P + [(CODE, "client.explain_why(decision_id)", False), (MUTED, "   # ×4 — every step above is evidence-bearing", False)]),
    (26, [(GREEN, "✓ CURRENT", True), (MUTED, "  policy, version, and publication cited for every decision served", False)]),
    # Footer.
    (42, [(FOOT, "One brief · eleven governed calls · twelve tables · eighteen policies · typed decisions — offline or live", False)]),
]

Y_START = 70
IDLE_GAP = 32


def _keytimes(index: int) -> str:
    reveal = REVEAL_START + index * REVEAL_STEP
    return f"0; {max(reveal - EPSILON, 0):.4f}; {reveal:.4f}; {HOLD:.4f}; {FADE:.4f}; 1"


def _animate(index: int) -> str:
    return (
        f'      <animate attributeName="opacity" values="0;0;1;1;0;0" '
        f'keyTimes="{_keytimes(index)}" dur="{DUR:.0f}s" repeatCount="indefinite"/>'
    )


def _spans(spans: list[tuple[str, str, bool]]) -> str:
    parts = []
    for color, text, bold in spans:
        weight = ' font-weight="bold"' if bold else ""
        parts.append(f'<tspan fill="{color}"{weight}>{escape(text)}</tspan>')
    return "".join(parts)


def render() -> str:
    lines = []
    y = Y_START
    for index, (gap, spans) in enumerate(STORYBOARD):
        y += gap
        lines.append(
            f'    <text x="24" y="{y}">\n'
            f"      {_spans(spans)}\n"
            f"{_animate(index)}\n"
            f"    </text>"
        )
    idle_y = y + IDLE_GAP
    height = idle_y + 32
    idle = (
        "    <g>\n"
        f'      <text x="24" y="{idle_y}" fill="{GREEN}">&gt;&gt;&gt;</text>\n'
        f'      <rect x="56" y="{idle_y - 11}" width="8" height="14" fill="{GREEN}">\n'
        '        <animate attributeName="opacity" values="1;1;0;0;1" keyTimes="0;0.45;0.5;0.95;1" dur="1.2s" repeatCount="indefinite"/>\n'
        "      </rect>\n"
        f"{_animate(len(STORYBOARD))}\n"
        "    </g>"
    )
    body = "\n\n".join(lines)
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="{WIDTH}" height="{height}" font-family="ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace" font-size="13" role="img" aria-label="{escape(ARIA)}">
  <title>Metatate examples — the governed agent, end to end</title>
  <desc>{escape(DESC)}</desc>

  <defs>
    <clipPath id="screen">
      <rect x="0" y="34" width="{WIDTH}" height="{height - 34}"/>
    </clipPath>
  </defs>

  <!-- terminal chrome -->
  <rect width="{WIDTH}" height="{height}" rx="10" fill="{BG}"/>
  <rect width="{WIDTH}" height="34" rx="10" fill="{CHROME}"/>
  <rect y="26" width="{WIDTH}" height="8" fill="{CHROME}"/>
  <circle cx="22" cy="17" r="6" fill="#ff5f56"/>
  <circle cx="42" cy="17" r="6" fill="#ffbd2e"/>
  <circle cx="62" cy="17" r="6" fill="#27c93f"/>
  <text x="{WIDTH // 2}" y="21" text-anchor="middle" fill="{MUTED}" font-size="12">metatate-examples · one agent brief, governed end to end</text>
  <line x1="0" y1="34" x2="{WIDTH}" y2="34" stroke="{RULE}" stroke-width="1"/>

  <g clip-path="url(#screen)">

{body}

{idle}

  </g>
</svg>
"""


def main() -> int:
    rendered = render()
    if "--check" in sys.argv[1:]:
        current = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
        if current != rendered:
            print("docs/assets/readme-hero.svg drifted from scripts/build_readme_hero.py", file=sys.stderr)
            return 1
        print("readme hero matches scripts/build_readme_hero.py")
        return 0
    TARGET.write_text(rendered, encoding="utf-8")
    print(f"wrote {TARGET.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
