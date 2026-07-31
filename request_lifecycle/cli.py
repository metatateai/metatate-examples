#!/usr/bin/env python3
"""CLI for the preview-by-default access-request lifecycle."""

from __future__ import annotations

import argparse
import json
import os
import sys

from common.saas_client import MetatateCloudClient
from request_lifecycle.workflow import preview, retry_with_active_exception, status, submit


def _live_client() -> MetatateCloudClient:
    if os.getenv("METATATE_EXAMPLES_MODE", "").strip().lower() != "live":
        raise SystemExit("Live request operations require METATATE_EXAMPLES_MODE=live")
    return MetatateCloudClient()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-submit", action="store_true", help="run the confirmed write flow")
    parser.add_argument("--tenant-slug", help="workspace slug used for the Activity deep link")
    parser.add_argument("--request-id", help="read one request owned by the current token")
    parser.add_argument("--retry", action="store_true", help="retry with an active granted exception")
    args = parser.parse_args()

    if args.live_submit:
        if args.request_id or args.retry:
            parser.error("--live-submit cannot be combined with --request-id/--retry")
        if not args.tenant_slug:
            parser.error("--live-submit requires --tenant-slug")
        if not sys.stdin.isatty():
            raise SystemExit("Refusing live submission without an interactive TTY")
        result = submit(_live_client(), args.tenant_slug)
        if result is not None:
            print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.request_id:
        client = _live_client()
        result = (
            retry_with_active_exception(client, args.request_id)
            if args.retry
            else status(client, args.request_id)
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    if args.retry:
        parser.error("--retry requires --request-id")
    print(json.dumps(preview(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
