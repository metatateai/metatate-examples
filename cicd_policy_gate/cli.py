#!/usr/bin/env python3
"""Command-line entry point for the CI/CD policy gate."""

from __future__ import annotations

import sys

from .gate import main


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
