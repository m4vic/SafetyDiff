from __future__ import annotations

import argparse
import os
from pathlib import Path


DEFAULT_DB = str(Path(__file__).parent.parent / "demo_safety_history.db")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="safetydiff",
        description="Compare AI safety run records.",
    )
    subparsers = parser.add_subparsers(dest="command")

    # --- compare subcommand ---
    compare = subparsers.add_parser("compare", help="Compare two run JSON files or database targets")
    compare.add_argument("old_run", help="Baseline run JSON or model/target name in DB")
    compare.add_argument("new_run", help="New run JSON or model/target name in DB")
    compare.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite database containing run history")
    compare.add_argument("--out", help="Optional report output path")
    compare.add_argument("--auto-run", action="store_true", default=True,
                         help="Automatically launch ASRT if data is missing (default: True)")
    compare.add_argument("--no-auto-run", action="store_false", dest="auto_run",
                         help="Disable auto-launching ASRT for missing data")
    compare.add_argument("--max-attacks", type=int, default=860,
                         help="Number of attacks to run if ASRT is auto-launched")

    # --- list subcommand ---
    list_cmd = subparsers.add_parser("list", help="List all models with evaluation data in the database")
    list_cmd.add_argument("--db", default=DEFAULT_DB, help="Path to SQLite database")

    args = parser.parse_args()

    if args.command == "list":
        from safetydiff.auto_runner import get_available_models
        models = get_available_models(args.db)
        if models:
            print(f"\nModels with evaluation data in '{args.db}':")
            for m in models:
                print(f"  - {m}")
        else:
            print("No models found in database.")
        return

    if args.command == "compare":
        from safetydiff.loader import load_run, load_run_from_db
        from safetydiff.diff import compare_runs
        from safetydiff.report import export_report

        db_path = args.db

        # --- Auto-Runner: detect missing data and delegate to ASRT ---
        if db_path and args.auto_run:
            from safetydiff.auto_runner import auto_run_if_needed
            ready = auto_run_if_needed(
                db_path=db_path,
                old_model=args.old_run,
                new_model=args.new_run,
                max_attacks=args.max_attacks,
                interactive=True,
            )
            if not ready:
                print("\n[!] Cannot generate diff. Missing evaluation data.")
                return

        # --- Load data ---
        if db_path and Path(db_path).exists():
            print(f"Loading baseline '{args.old_run}' from database {db_path}...")
            old_run = load_run_from_db(db_path, args.old_run)

            print(f"Loading comparison '{args.new_run}' from database {db_path}...")
            new_run = load_run_from_db(db_path, args.new_run)
        else:
            print(f"Loading old run from {args.old_run}...")
            old_run = load_run(args.old_run)

            print(f"Loading new run from {args.new_run}...")
            new_run = load_run(args.new_run)

        # --- Generate Diff ---
        print("Comparing runs...")
        report = compare_runs(old_run, new_run)

        out_path = args.out or "safety_diff_report.md"
        export_report(report, out_path, format="markdown")
        print(f"Report exported to {out_path}")
        return

    parser.print_help()


if __name__ == "__main__":
    main()

