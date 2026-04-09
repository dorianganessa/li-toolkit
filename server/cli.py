"""CLI for li-toolkit — interact with your LinkedIn data without running a server."""

import argparse
import json
import sys

from database import SessionLocal, init_db
from services import (
    analyze_draft as svc_analyze_draft,
)
from services import (
    get_analytics,
    get_post_count,
    get_recent_velocity,
    get_recommendations,
    get_strategy,
    get_strategy_suggestions,
    get_top_posts,
    get_trends,
    get_velocity,
    list_posts,
    search_posts,
)


def _get_db():
    return SessionLocal()


def _output(data, pretty: bool = False) -> None:
    """Print data as JSON (default) or human-readable text."""
    if pretty:
        _print_pretty(data)
    else:
        print(json.dumps(data, default=str, indent=2))


def _print_pretty(data) -> None:
    """Simple human-readable formatting."""
    if isinstance(data, list):
        for i, item in enumerate(data):
            if isinstance(item, dict):
                _print_dict_short(item, index=i + 1)
            else:
                print(f"  {item}")
        if not data:
            print("  (no results)")
    elif isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, (list, dict)):
                print(f"\n{key}:")
                _print_pretty(val)
            else:
                print(f"  {key}: {val}")
    else:
        print(data)


def _print_dict_short(d: dict, index: int | None = None) -> None:
    """Print a dict as a compact one-liner with key fields."""
    prefix = f"  {index}. " if index else "  "
    text = d.get("text", "")
    if len(text) > 80:
        text = text[:80] + "..."
    likes = d.get("likes", d.get("engagement_score", ""))
    comments = d.get("comments", "")
    impressions = d.get("impressions", "")
    parts = [text]
    if likes:
        parts.append(f"likes={likes}")
    if comments:
        parts.append(f"comments={comments}")
    if impressions:
        parts.append(f"impressions={impressions}")
    print(f"{prefix}{' | '.join(parts)}")


def cmd_posts(args) -> None:
    db = _get_db()
    try:
        data = list_posts(db, limit=args.limit, offset=args.offset)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_top(args) -> None:
    db = _get_db()
    try:
        data = get_top_posts(db, count=args.count)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_search(args) -> None:
    db = _get_db()
    try:
        data = search_posts(db, query=args.query, limit=args.limit)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_analytics(args) -> None:
    db = _get_db()
    try:
        data = get_analytics(db)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_draft(args) -> None:
    if args.stdin:
        text = sys.stdin.read().strip()
    else:
        text = args.text
    if not text:
        print("Error: provide draft text or use --stdin", file=sys.stderr)
        sys.exit(1)
    db = _get_db()
    try:
        data = svc_analyze_draft(db, text)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_trends(args) -> None:
    db = _get_db()
    try:
        data = get_trends(db, days=args.days)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_recommendations(args) -> None:
    db = _get_db()
    try:
        data = get_recommendations(db)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_velocity(args) -> None:
    db = _get_db()
    try:
        if args.post_id:
            data = get_velocity(db, args.post_id)
        else:
            data = get_recent_velocity(db, count=args.count)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_strategy(args) -> None:
    data = get_strategy()
    _output(data, args.pretty)


def cmd_suggest(args) -> None:
    db = _get_db()
    try:
        data = get_strategy_suggestions(db)
        _output(data, args.pretty)
    finally:
        db.close()


def cmd_count(args) -> None:
    db = _get_db()
    try:
        n = get_post_count(db)
        _output({"count": n}, args.pretty)
    finally:
        db.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="li-toolkit",
        description="LinkedIn post analytics CLI",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    def _add_pretty(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--pretty", "-p", action="store_true",
            help="Human-readable output instead of JSON",
        )

    # posts
    p = sub.add_parser("posts", help="List posts")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--offset", type=int, default=0)
    _add_pretty(p)
    p.set_defaults(func=cmd_posts)

    # top
    p = sub.add_parser("top", help="Top posts by engagement")
    p.add_argument("--count", type=int, default=5)
    _add_pretty(p)
    p.set_defaults(func=cmd_top)

    # search
    p = sub.add_parser("search", help="Search posts")
    p.add_argument("query", help="Search term")
    p.add_argument("--limit", type=int, default=20)
    _add_pretty(p)
    p.set_defaults(func=cmd_search)

    # analytics
    p = sub.add_parser("analytics", help="Full analytics")
    _add_pretty(p)
    p.set_defaults(func=cmd_analytics)

    # draft
    p = sub.add_parser("draft", help="Analyze a draft post")
    p.add_argument("text", nargs="?", default="", help="Draft text")
    p.add_argument(
        "--stdin", action="store_true",
        help="Read draft from stdin",
    )
    _add_pretty(p)
    p.set_defaults(func=cmd_draft)

    # trends
    p = sub.add_parser("trends", help="Engagement trends")
    p.add_argument("--days", type=int, default=90)
    _add_pretty(p)
    p.set_defaults(func=cmd_trends)

    # recommendations
    p = sub.add_parser(
        "recommendations", help="Posting recommendations",
    )
    _add_pretty(p)
    p.set_defaults(func=cmd_recommendations)

    # velocity
    p = sub.add_parser("velocity", help="Engagement velocity")
    p.add_argument("--post-id", type=int, default=None)
    p.add_argument("--count", type=int, default=5)
    _add_pretty(p)
    p.set_defaults(func=cmd_velocity)

    # strategy
    p = sub.add_parser("strategy", help="View content strategy")
    _add_pretty(p)
    p.set_defaults(func=cmd_strategy)

    # suggest
    p = sub.add_parser(
        "suggest", help="Data-driven strategy suggestions",
    )
    _add_pretty(p)
    p.set_defaults(func=cmd_suggest)

    # count
    p = sub.add_parser("count", help="Total post count")
    _add_pretty(p)
    p.set_defaults(func=cmd_count)

    return parser


def main() -> None:
    init_db()
    parser = _build_parser()
    args = parser.parse_args()
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
