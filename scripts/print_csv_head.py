#!/usr/bin/env python3
"""
Print the first 5 rows of a CSV file.

Usage:
  python scripts/print_csv_head.py path/to/file.csv [--skip-header] [--delimiter ,] [--encoding utf-8]
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Print the first 5 rows of a CSV file")
    p.add_argument("csv_path", type=Path, help="Path to the CSV file")
    p.add_argument("--skip-header", action="store_true", help="Skip the first row (treat as header)")
    p.add_argument("--delimiter", default=None, help="CSV delimiter (auto-detect if omitted)")
    p.add_argument("--encoding", default="utf-8", help="File encoding (default: utf-8)")
    p.add_argument("--rows", type=int, default=5, help="Number of rows to print (default: 5)")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if not args.csv_path.exists():
        print(f"Error: file not found: {args.csv_path}", file=sys.stderr)
        return 1

    try:
        with args.csv_path.open("r", encoding=args.encoding, newline="") as f:
            sample = f.read(4096)
            f.seek(0)
            dialect = None
            if args.delimiter:
                # Create a simple dialect using the provided delimiter
                class _D(csv.Dialect):
                    delimiter = args.delimiter
                    quotechar = '"'
                    doublequote = True
                    escapechar = None
                    lineterminator = "\n"
                    quoting = csv.QUOTE_MINIMAL

                dialect = _D
            else:
                try:
                    dialect = csv.Sniffer().sniff(sample)
                except Exception:
                    # Fallback to common CSV defaults
                    dialect = csv.excel

            reader = csv.reader(f, dialect=dialect)

            if args.skip_header:
                next(reader, None)

            writer = csv.writer(sys.stdout, dialect=dialect)
            count = 0
            for row in reader:
                writer.writerow(row)
                count += 1
                if count >= args.rows:
                    break
    except UnicodeDecodeError:
        print(
            "Error: failed to decode file. Try --encoding latin-1 (or another).",
            file=sys.stderr,
        )
        return 1
    except OSError as e:
        print(f"Error reading file: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

