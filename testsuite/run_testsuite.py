#!/usr/bin/env python3.11
# Copyright (c) 2026 SUSE LLC
# Licensed under the terms of the MIT license.
"""
Uyuni testsuite runner — Python/pytest-bdd equivalent of `rake cucumber:<name>`.

Usage:
    ./run_testsuite.py core
    ./run_testsuite.py sanity_check --report both
    ./run_testsuite.py --feature srv_first_settings
    ./run_testsuite.py --list
    ./run_testsuite.py core -- -x --tb=short

Terracumber equivalent:
    rake cucumber:core  →  ./run_testsuite.py core
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

TESTSUITE_DIR = Path(__file__).parent.resolve()
RUN_SETS_DIR = TESTSUITE_DIR / "run_sets"

# openSUSE packages Node as 'node20'; other distros use 'node'
_NODE_BIN = shutil.which("node") or shutil.which("node20") or "node"
DEFAULT_OUTPUT_DIR = TESTSUITE_DIR / "results"


# ---------------------------------------------------------------------------
# Run-set discovery
# ---------------------------------------------------------------------------

def _all_run_sets() -> list[tuple[str, Path]]:
    """Return [(display_name, path)] for every run_set YAML, sorted."""
    results = []
    for yml in sorted(RUN_SETS_DIR.rglob("*.yml")):
        rel = yml.relative_to(RUN_SETS_DIR)
        # Build a human-readable name: build_validation/core.yml → build_validation:core
        name = str(rel.with_suffix("")).replace(os.sep, ":")
        results.append((name, yml))
    return results


def _find_run_set(name: str) -> Path:
    """Locate a run_set YAML by name. Accepts 'core', 'build_validation:core', etc."""
    # Normalise separators
    normalised = name.replace(":", os.sep).replace("/", os.sep)

    # Exact match first
    exact = RUN_SETS_DIR / (normalised + ".yml")
    if exact.exists():
        return exact

    # Basename search (allows 'core' to match 'build_validation/core.yml' if unambiguous)
    basename = Path(normalised).name
    matches = list(RUN_SETS_DIR.rglob(f"{basename}.yml"))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = [str(m.relative_to(RUN_SETS_DIR)) for m in matches]
        _die(
            f"Ambiguous run set '{name}'. Did you mean one of:\n"
            + "\n".join(f"  {n}" for n in names)
        )
    _die(
        f"Run set '{name}' not found. Use --list to see available run sets."
    )


def _count_features(yml: Path) -> int:
    return sum(
        1 for line in yml.read_text(errors="replace").splitlines()
        if line.strip().startswith("- features/")
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _die(msg: str) -> None:
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def _header(msg: str) -> None:
    width = max(len(msg) + 4, 60)
    print("=" * width)
    print(f"  {msg}")
    print("=" * width)


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------

def _build_pytest_cmd(args: argparse.Namespace, output_dir: Path) -> list[str]:
    cmd = [sys.executable, "-m", "pytest"]

    # Run set filter
    if args.run_set:
        cmd.append(f"--run-set={args.run_set}")

    # Single feature keyword filter
    if args.feature:
        cmd += ["-k", args.feature]

    # Verbosity
    if not args.quiet:
        cmd.append("-v")

    # Stop on first failure
    if args.exitfirst:
        cmd.append("-x")

    # Gherkin terminal reporter (cleaner BDD output)
    if args.gherkin:
        cmd.append("--gherkin-terminal-reporter")

    # Cucumber JSON — named output_pytest.json so index.cjs picks it up (output_*.json pattern)
    if args.report in ("cucumber", "both"):
        cmd.append(f"--cucumberjson={output_dir / 'output_pytest.json'}")

    # pytest-html
    if args.report in ("html", "both"):
        cmd += [f"--html={output_dir / 'report.html'}", "--self-contained-html"]

    # JUnit XML (useful for Jenkins)
    if args.junit:
        cmd.append(f"--junit-xml={output_dir / 'junit.xml'}")

    # Passthrough pytest arguments (after --)
    cmd += args.extra

    return cmd


def _generate_mchr(output_dir: Path, title: str) -> None:
    """Generate HTML from Cucumber JSON using index.cjs (calls multiple-cucumber-html-reporter programmatically)."""
    json_path = output_dir / "output_pytest.json"
    if not json_path.exists():
        print("  (no output_pytest.json to process)")
        return

    index_cjs = TESTSUITE_DIR / "index.cjs"
    if not index_cjs.exists():
        print(f"  Note: {index_cjs} not found — skipping Cucumber HTML report.")
        return

    # index.cjs writes to cucumber_report/ relative to cwd (TESTSUITE_DIR)
    report_src = TESTSUITE_DIR / "cucumber_report"
    html_dir = output_dir / "html"

    try:
        result = subprocess.run(
            [_NODE_BIN, str(index_cjs), str(output_dir)],
            capture_output=True,
            text=True,
            timeout=120,
            cwd=TESTSUITE_DIR,
        )
        if result.returncode == 0 and report_src.exists():
            html_dir.mkdir(exist_ok=True)
            shutil.copytree(str(report_src), str(html_dir), dirs_exist_ok=True)
            print(f"  Cucumber HTML report → {html_dir}/index.html")
        else:
            print(f"  Warning: index.cjs failed (exit {result.returncode}):\n{result.stderr[:300]}")
            if result.stdout:
                print(result.stdout[:200])
    except FileNotFoundError:
        print("  Note: node not found — skipping Cucumber HTML report.")
    except subprocess.TimeoutExpired:
        print("  Warning: HTML report generation timed out.")


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------

def cmd_list(_args: argparse.Namespace) -> int:
    print(f"Available run sets ({RUN_SETS_DIR}):\n")
    for name, yml in _all_run_sets():
        count = _count_features(yml)
        print(f"  {name:<45}  ({count} feature{'s' if count != 1 else ''})")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    # Resolve output directory
    output_dir = (args.output_dir or DEFAULT_OUTPUT_DIR).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "screenshots").mkdir(exist_ok=True)

    # Environment
    os.environ.setdefault("SCREENSHOT_DIR", str(output_dir / "screenshots"))
    if args.debug:
        os.environ["DEBUG"] = "true"
    if args.server:
        os.environ["SERVER"] = args.server

    # Build command
    os.chdir(TESTSUITE_DIR)
    cmd = _build_pytest_cmd(args, output_dir)

    # Print header
    label = args.run_set or args.feature or "(custom)"
    _header(f"Uyuni Testsuite — {label}")
    print(f"  Command:    {' '.join(cmd)}")
    print(f"  Output dir: {output_dir}/")
    if args.debug:
        print("  Mode:       headed browser (DEBUG=true)")
    print()

    # Run
    result = subprocess.run(cmd)

    # Post-run: generate Cucumber HTML if requested
    print()
    if args.report == "both":
        print("Generating Cucumber HTML report...")
        _generate_mchr(output_dir, f"SUMA Testsuite — {label}")

    # Summary
    print()
    print("─" * 60)
    print("Output:")
    if args.report in ("cucumber", "both"):
        p = output_dir / "output_pytest.json"
        if p.exists():
            print(f"  Cucumber JSON  → {p}")
    if args.report in ("html", "both"):
        p = output_dir / "report.html"
        if p.exists():
            print(f"  HTML report    → {p}")
    if args.report == "both":
        p = output_dir / "html" / "index.html"
        if p.exists():
            print(f"  Cucumber HTML  → {p}")
    if args.junit:
        p = output_dir / "junit.xml"
        if p.exists():
            print(f"  JUnit XML      → {p}")
    screenshots = sorted((output_dir / "screenshots").glob("*.png"))
    if screenshots:
        print(f"  Screenshots    → {output_dir}/screenshots/  ({len(screenshots)} file(s))")
    print("─" * 60)
    status = "PASSED" if result.returncode == 0 else "FAILED"
    print(f"  Result: {status}")
    print("─" * 60)

    return result.returncode


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_testsuite.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Positional run-set name (makes it feel like `rake cucumber:core`)
    parser.add_argument(
        "run_set",
        nargs="?",
        metavar="RUN_SET",
        help="Run set name (e.g. core, sanity_check, build_validation:build_validation_core). "
             "Equivalent to `rake cucumber:<name>`.",
    )

    # Selection
    select = parser.add_argument_group("selection")
    select.add_argument(
        "--run-set", dest="run_set_flag", metavar="NAME",
        help="Run set name (alternative to positional argument).",
    )
    select.add_argument(
        "--feature", metavar="STEM",
        help="Run a single feature file by stem, e.g. --feature srv_first_settings.",
    )

    # Output
    out = parser.add_argument_group("output")
    out.add_argument(
        "--report",
        choices=["cucumber", "html", "both", "none"],
        default="cucumber",
        help="Report format. 'cucumber' = Cucumber JSON (Jenkins plugin compatible). "
             "'html' = self-contained HTML with embedded screenshots. "
             "'both' = Cucumber JSON + multiple-cucumber-html-reporter HTML. "
             "Default: cucumber.",
    )
    out.add_argument(
        "--output-dir", metavar="DIR", type=Path, default=None,
        help=f"Directory for reports and screenshots (default: {DEFAULT_OUTPUT_DIR}).",
    )
    out.add_argument(
        "--junit", action="store_true",
        help="Also write a JUnit XML report (for Jenkins).",
    )

    # Browser / environment
    env = parser.add_argument_group("environment")
    env.add_argument(
        "--server", metavar="HOST",
        help="SUMA/Uyuni server hostname (sets SERVER env var).",
    )
    env.add_argument(
        "--debug", action="store_true",
        help="Run browser in headed (visible) mode.",
    )

    # pytest tuning
    tuning = parser.add_argument_group("pytest options")
    tuning.add_argument(
        "-q", "--quiet", action="store_true",
        help="Suppress verbose pytest output.",
    )
    tuning.add_argument(
        "-x", "--exitfirst", action="store_true",
        help="Stop after the first failure.",
    )
    tuning.add_argument(
        "--gherkin", action="store_true",
        help="Use pytest-bdd's Gherkin terminal reporter (cleaner BDD output).",
    )

    # Utility
    parser.add_argument(
        "--list", action="store_true",
        help="List all available run sets and exit.",
    )

    return parser


def main() -> int:
    parser = _build_parser()
    args, extra = parser.parse_known_args()

    # Strip leading '--' separator from passthrough args
    if extra and extra[0] == "--":
        extra = extra[1:]
    args.extra = extra

    # --list
    if args.list:
        return cmd_list(args)

    # Merge positional run_set with --run-set flag
    run_set_value = args.run_set or args.run_set_flag
    if run_set_value:
        # Validate it exists
        _find_run_set(run_set_value)
        args.run_set = run_set_value
    else:
        args.run_set = None

    # Need something to run
    if not args.run_set and not args.feature and not args.extra:
        parser.print_help()
        return 1

    return cmd_run(args)


if __name__ == "__main__":
    sys.exit(main())
