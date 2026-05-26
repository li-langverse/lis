"""lis CLI — `lis db` supervisor (PH-DB-3 / WP-I)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from lis.db.supervisor import DbSupervisor


def _cmd_db_start(args: argparse.Namespace) -> int:
    sup = DbSupervisor(
        data_dir=None if args.data_dir is None else Path(args.data_dir),
        profile_name=args.profile,
    )
    if args.foreground:
        try:
            sup.run_foreground(interval_sec=args.interval)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    state = sup.start()
    if args.json:
        print(json.dumps(state, indent=2))
    else:
        print(f"lis db: ready={state['ready']} profile={state['profile']} data_dir={state['data_dir']}")
    return 0 if state.get("ready") else 1


def _cmd_db_migrate(args: argparse.Namespace) -> int:
    from pathlib import Path

    sup = DbSupervisor(
        data_dir=None if args.data_dir is None else Path(args.data_dir),
        profile_name=args.profile,
    )
    if not sup.migrate():
        print("lis db migrate: failed", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({"migrated": True, "data_dir": str(sup.data_dir)}, indent=2))
    else:
        print(f"lis db migrate: ok data_dir={sup.data_dir}")
    return 0


def _cmd_db_status(args: argparse.Namespace) -> int:
    from pathlib import Path

    sup = DbSupervisor(
        data_dir=None if args.data_dir is None else Path(args.data_dir),
        profile_name=args.profile,
    )
    payload = sup.status()
    print(json.dumps(payload, indent=2 if args.json else None))
    return 0 if payload.get("ready") else 1


def _cmd_db_stop(args: argparse.Namespace) -> int:
    sup = DbSupervisor(
        data_dir=None if args.data_dir is None else Path(args.data_dir),
        profile_name=args.profile,
    )
    sup.stop()
    if args.json:
        print(json.dumps({"stopped": True, "data_dir": str(sup.data_dir)}))
    else:
        print(f"lis db stop: ok data_dir={sup.data_dir}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lis", description="Li ecosystem supervisor")
    sub = parser.add_subparsers(dest="command", required=True)

    db = sub.add_parser("db", help="Embedded lidb supervisor (PH-DB-3)")
    db_sub = db.add_subparsers(dest="db_command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--profile", default=None, help="Profile name (default: LI_PROFILE or registry-min)")
    common.add_argument("--data-dir", dest="data_dir", default=None, help="LI_DATA_DIR override")
    common.add_argument("--json", action="store_true", help="Machine-readable output")

    start_p = db_sub.add_parser("start", parents=[common], help="lis db start")
    start_p.add_argument(
        "--foreground",
        action="store_true",
        help="Run until SIGTERM; emit startup JSON then periodic readiness probes (WP-I hosting)",
    )
    start_p.add_argument(
        "--interval",
        type=int,
        default=None,
        help="Foreground probe interval seconds (default: profile hosting.liveness_interval_sec or 30)",
    )
    start_p.set_defaults(handler=_cmd_db_start)

    for name, handler in (
        ("migrate", _cmd_db_migrate),
        ("status", _cmd_db_status),
        ("stop", _cmd_db_stop),
    ):
        p = db_sub.add_parser(name, parents=[common], help=f"lis db {name}")
        p.set_defaults(handler=handler)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "db":
        return args.handler(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
