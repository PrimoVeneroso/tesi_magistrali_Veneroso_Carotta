"""CLI: python -m pipeline <extract|merge|classify|audit|releases>"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipeline.audit import audit_classification
from pipeline.classify import classify_terms
from pipeline.config import Settings
from pipeline.extract import crawl, list_releases
from pipeline.merge import merge_datasets


def _load_json(path: Path) -> list | dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _dump_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"Scritto {path}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Pipeline ICD-11: estrazione, fusione, classificazione EM/EF/EE."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    releases = sub.add_parser("releases", help="Elenca le release MMS esposte dall'API")
    releases.add_argument("--api-base", default=None)

    extract = sub.add_parser("extract", help="Crawl BFS da ICD-API")
    extract.add_argument("--target", choices=("mms", "foundation"), required=True)
    extract.add_argument("--out", type=Path, required=True)
    extract.add_argument("--release", default=None)
    extract.add_argument("--linearization", default=None)
    extract.add_argument("--language", default=None)
    extract.add_argument("--api-base", default=None)

    merge = sub.add_parser("merge", help="Normalizza e fonde MMS + Foundation")
    merge.add_argument("--mms", type=Path, required=True)
    merge.add_argument("--foundation", type=Path, required=True)
    merge.add_argument("--out", type=Path, required=True)
    merge.add_argument("--release", default="")

    classify = sub.add_parser("classify", help="Classifica termini EE e recupera link")
    classify.add_argument("--merged", type=Path, required=True)
    classify.add_argument("--out", type=Path, required=True)

    audit = sub.add_parser("audit", help="Verifica EM/EF/EE rispetto ai dump originali")
    audit.add_argument("--merged", type=Path, required=True)
    audit.add_argument("--mms", type=Path, required=True)
    audit.add_argument("--foundation", type=Path, required=True)
    audit.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "releases":
        settings = Settings.from_env(api_base=getattr(args, "api_base", None) or None)
        found = list_releases(settings)
        print("Release disponibili:")
        for item in found:
            print(f"  {item}")
        if not found:
            print("  (nessuna: verifica che l'ICD-API Docker sia in esecuzione)")
        return 0

    if args.command == "extract":
        settings = Settings.from_env(
            release=args.release,
            linearization=args.linearization,
            language=args.language,
            api_base=args.api_base,
        )
        root = settings.linearization_root if args.target == "mms" else settings.foundation_root
        print(f"Crawl {args.target} da {root} (API {settings.api_base})")
        crawl(root, settings, output=args.out)
        return 0

    if args.command == "merge":
        mms = _load_json(args.mms)
        foundation = _load_json(args.foundation)
        merged = merge_datasets(mms, foundation, release=args.release)
        _dump_json(args.out, merged)
        print(merged["counts"])
        return 0

    if args.command == "classify":
        merged = _load_json(args.merged)
        classified = classify_terms(merged)
        _dump_json(args.out, classified)
        print(classified["counts"])
        print(classified["audit"]["term_stats"])
        return 0

    if args.command == "audit":
        merged = _load_json(args.merged)
        if "external_terms" not in merged:
            merged = classify_terms(merged)
        report = audit_classification(
            merged, _load_json(args.mms), _load_json(args.foundation)
        )
        _dump_json(args.out, report)
        status = "PASS" if report["passed"] else "FAIL"
        print(f"Audit {status}")
        for check in report["checks"]:
            mark = "ok" if check["passed"] else "FAIL"
            print(f"  [{mark}] {check['name']}: {check['observed']}")
        return 0 if report["passed"] else 1

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
