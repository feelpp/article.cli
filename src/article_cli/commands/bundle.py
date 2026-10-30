"""Source archive command for HAL, arXiv, and other submission systems."""

import argparse
import subprocess

from ..config import Config
from ..reporting import print_error, print_info, print_success
from ..services.bundle import BundleOptions, BundleService


def add_parser(subparsers):
    parser = subparsers.add_parser("bundle", help="Create a LaTeX or Typst source ZIP")
    parser.add_argument(
        "document", nargs="?", help="Main .tex or .typ file (or configured document)"
    )
    parser.add_argument(
        "-o", "--output", help="ZIP path, relative to document directory"
    )
    parser.add_argument(
        "--build-dir", help="Build directory containing compiler dependency metadata"
    )
    parser.add_argument(
        "--include",
        action="append",
        default=[],
        help="Add document-relative glob (repeatable)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        help="Exclude document-relative glob (repeatable)",
    )
    for key, help_text in [
        ("verify", "Recompile selected files in a clean directory"),
        ("include-pdf", "Include the generated main PDF in the ZIP"),
    ]:
        group = parser.add_mutually_exclusive_group()
        group.add_argument(
            "--" + key,
            dest=key.replace("-", "_"),
            action="store_true",
            default=None,
            help=help_text,
        )
        group.add_argument(
            "--no-" + key, dest=key.replace("-", "_"), action="store_false"
        )
    parser.add_argument(
        "--no-build",
        action="store_true",
        help="Use existing compiler dependency metadata and PDF",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files from existing build data; write nothing",
    )
    parser.add_argument(
        "--force", action="store_true", help="Replace an existing ZIP and manifest"
    )
    parser.set_defaults(handler=run)


def run(args: argparse.Namespace, config: Config) -> int:
    try:
        service = BundleService(config)
        plan = service.plan(
            BundleOptions(
                document=args.document,
                output=args.output,
                build_dir=args.build_dir,
                include=tuple(args.include),
                exclude=tuple(args.exclude),
                include_pdf=args.include_pdf,
                verify=args.verify,
                no_build=args.no_build,
                dry_run=args.dry_run,
            )
        )
        print_info(f"Bundle files ({len(plan.files)}):")
        for name in sorted(plan.files):
            print(f"  {name}")
        if args.dry_run:
            print_info(f"Would write: {plan.output}")
        else:
            output = service.write(plan, force=args.force)
            print_success(f"Created source bundle: {output}")
            print_info(f'Manifest: {output.with_suffix(".manifest.json")}')
        return 0
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        print_error(str(error))
        return 1
