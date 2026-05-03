#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set, Tuple


def iter_assets(data: Dict[str, Any], collection: str) -> Iterable[Dict[str, Any]]:
    assets_toa = data.get("assets_toa")
    if not isinstance(assets_toa, dict):
        return []
    items = assets_toa.get(collection)
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def sha1_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    h = hashlib.sha1()
    with path.open("rb") as fh:
        while True:
            chunk = fh.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def collect_expected_source_files(
    data: Dict[str, Any], source_root: Path, collection: str
) -> Tuple[List[Path], List[str]]:
    expected: List[Path] = []
    problems: List[str] = []

    for asset in iter_assets(data, collection):
        kernel_path = asset.get("kernel_path")
        if not isinstance(kernel_path, str) or not kernel_path.strip():
            continue

        source_file = source_root / Path(kernel_path.replace("\\", "/"))
        if not source_file.exists():
            problems.append(f"[missing source] {source_file}")
            continue

        if source_file.is_file() and source_file.suffix.lower() == ".html":
            package_dir = source_file.parent
            package_files = [p for p in package_dir.rglob("*") if p.is_file()]
            if not package_files:
                problems.append(f"[empty package] {package_dir}")
            expected.extend(package_files)
            continue

        if source_file.is_file():
            expected.append(source_file)
        else:
            problems.append(f"[not a file] {source_file}")

    # Deduplicate while keeping deterministic ordering.
    unique = sorted(set(expected))
    return unique, problems


def build_signature_index(files: Iterable[Path]) -> Set[Tuple[int, str]]:
    signatures: Set[Tuple[int, str]] = set()
    for path in files:
        size = path.stat().st_size
        digest = sha1_file(path)
        signatures.add((size, digest))
    return signatures


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Check which expected asset files are missing in the copied output."
        )
    )
    parser.add_argument("--json", default="json.json", help="Path to JSON file.")
    parser.add_argument(
        "--source-root",
        required=True,
        help="Root folder where kernel_path files are stored.",
    )
    parser.add_argument(
        "--output-root",
        default="assets_by_label",
        help="Folder where copied files were written.",
    )
    parser.add_argument(
        "--collection",
        default="resources",
        choices=["containers", "resources"],
        help="assets_toa collection to audit.",
    )
    parser.add_argument(
        "--report",
        default="missing_assets_report.txt",
        help="Path to write full missing-file report.",
    )
    args = parser.parse_args()

    json_path = Path(args.json)
    source_root = Path(args.source_root)
    output_root = Path(args.output_root)
    report_path = Path(args.report)

    with json_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    expected_files, source_problems = collect_expected_source_files(
        data=data, source_root=source_root, collection=args.collection
    )
    output_files = [p for p in output_root.rglob("*") if p.is_file()]

    print(f"expected source files: {len(expected_files)}")
    print(f"output files found: {len(output_files)}")

    print("building output signature index...")
    output_signatures = build_signature_index(output_files)

    missing: List[Path] = []
    for src in expected_files:
        sig = (src.stat().st_size, sha1_file(src))
        if sig not in output_signatures:
            missing.append(src)

    with report_path.open("w", encoding="utf-8") as rep:
        rep.write(f"collection: {args.collection}\n")
        rep.write(f"expected source files: {len(expected_files)}\n")
        rep.write(f"output files found: {len(output_files)}\n")
        rep.write(f"missing in output: {len(missing)}\n\n")

        if source_problems:
            rep.write("== Source problems ==\n")
            for line in source_problems:
                rep.write(f"{line}\n")
            rep.write("\n")

        rep.write("== Missing files ==\n")
        for path in missing:
            rep.write(f"{path}\n")

    print(f"source problems: {len(source_problems)}")
    print(f"missing in output: {len(missing)}")
    print(f"report written to: {report_path}")


if __name__ == "__main__":
    main()
