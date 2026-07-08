"""Ingestion layer: turns CI artifacts into ``TestRunRecord`` streams."""

from flakysense.ingest.junit import JUnitParseError, parse_junit_dir, parse_junit_file

__all__ = ["JUnitParseError", "parse_junit_dir", "parse_junit_file"]
