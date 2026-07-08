"""``python -m flakysense`` — same contract as the console script (ADR-006)."""

import sys

from flakysense.cli import main

if __name__ == "__main__":
    sys.exit(main())
