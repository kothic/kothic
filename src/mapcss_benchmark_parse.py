import argparse
import time
from pathlib import Path

from .mapcss import MapCSS, COMMENT, CONDITION, IMPORT, parseCondition


def read_stylesheet_sources(path, seen=None):
    if seen is None:
        seen = set()

    path = path.resolve()
    if path in seen:
        return []
    seen.add(path)

    source = path.read_text(encoding="utf-8")
    imported_sources = []
    uncommented_source = COMMENT.sub("", source)
    for match in IMPORT.finditer(uncommented_source):
        imported_path = path.parent / match.group(1)
        imported_sources.extend(read_stylesheet_sources(imported_path, seen))

    return [source, *imported_sources]


def read_stylesheet_tree(path, seen=None):
    return "".join(read_stylesheet_sources(path, seen))


def count_source_lines(source):
    if not source:
        return 0
    return source.count("\n") + (0 if source.endswith("\n") else 1)


def infer_static_tags(source):
    tags = {}
    source = COMMENT.sub("", source)
    for match in CONDITION.finditer(source):
        tag = parseCondition(match.group(1)).extract_tag()
        if tag != "*" and not tag.startswith("::"):
            tags[tag] = True

    return tags


def parse_style(path, minzoom=0, maxzoom=30, static_tags=None):
    source = path.read_text(encoding="utf-8")
    source_tree_parts = read_stylesheet_sources(path)
    source_tree = "".join(source_tree_parts)
    parser = MapCSS(minzoom, maxzoom)
    tags = static_tags if static_tags is not None else infer_static_tags(source_tree)

    started_at = time.perf_counter()
    parser.parse(source, filename=str(path), static_tags=tags)
    elapsed = time.perf_counter() - started_at

    return {
        "path": str(path),
        "bytes": sum(len(part.encode("utf-8")) for part in source_tree_parts),
        "lines": sum(count_source_lines(part) for part in source_tree_parts),
        "static_tags": len(tags),
        "seconds": elapsed,
        "choosers": len(parser.choosers),
        "rule_chains": sum(len(chooser.ruleChains) for chooser in parser.choosers),
    }


def format_report(stats):
    return "\n".join([
        "MapCSS parse benchmark",
        "path: %s" % stats["path"],
        "bytes: %s" % stats["bytes"],
        "lines: %s" % stats["lines"],
        "static_tags: %s" % stats["static_tags"],
        "seconds: %.6f" % stats["seconds"],
        "choosers: %s" % stats["choosers"],
        "rule_chains: %s" % stats["rule_chains"],
    ])


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Measure MapCSS parser wall time for a stylesheet."
    )
    parser.add_argument("stylesheet", type=Path, help="Path to a MapCSS stylesheet.")
    parser.add_argument("--minzoom", type=int, default=0)
    parser.add_argument("--maxzoom", type=int, default=30)
    parser.add_argument(
        "--tag",
        action="append",
        dest="tags",
        default=[],
        help="Known static tag. Can be passed multiple times. Defaults to simple selector inference.",
    )
    return parser


def main(argv=None):
    args = build_arg_parser().parse_args(argv)
    static_tags = {tag: True for tag in args.tags} if args.tags else None
    stats = parse_style(args.stylesheet, args.minzoom, args.maxzoom, static_tags)
    print(format_report(stats))


if __name__ == "__main__":
    main()
