#!/usr/bin/env python3
import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple


def safe_folder_name(name: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "_", name.strip())
    return cleaned or "unknown"


def collect_page_labels(node: Any, page_map: Dict[int, str]) -> None:
    if isinstance(node, dict):
        pages = node.get("pages")
        if isinstance(pages, list):
            for page in pages:
                if isinstance(page, dict):
                    page_id = page.get("id")
                    label = page.get("label")
                    if isinstance(page_id, int) and label is not None:
                        page_map[page_id] = str(label)

        for value in node.values():
            collect_page_labels(value, page_map)
    elif isinstance(node, list):
        for item in node:
            collect_page_labels(item, page_map)


def collect_root_pages_labels(data: Dict[str, Any]) -> Dict[int, str]:
    page_map: Dict[int, str] = {}
    pages = data.get("pages")
    if not isinstance(pages, list):
        return page_map

    for page in pages:
        if not isinstance(page, dict):
            continue
        page_id = page.get("id")
        label = page.get("label")
        if isinstance(page_id, int) and label is not None:
            page_map[page_id] = str(label)
    return page_map


def collect_page_id_to_number(node: Any, page_number_map: Dict[int, int]) -> None:
    if isinstance(node, dict):
        pages = node.get("pages")
        if isinstance(pages, list):
            for page in pages:
                if not isinstance(page, dict):
                    continue
                page_id = page.get("id")
                number = page.get("number")
                if isinstance(page_id, int) and isinstance(number, int):
                    page_number_map[page_id] = number
        for value in node.values():
            collect_page_id_to_number(value, page_number_map)
    elif isinstance(node, list):
        for item in node:
            collect_page_id_to_number(item, page_number_map)


def collect_root_label_by_number(data: Dict[str, Any]) -> Dict[int, str]:
    labels_by_number: Dict[int, str] = {}
    pages = data.get("pages")
    if not isinstance(pages, list):
        return labels_by_number

    for page in pages:
        if not isinstance(page, dict):
            continue
        number = page.get("number")
        label = page.get("label")
        if isinstance(number, int) and label is not None:
            labels_by_number[number] = str(label)
    return labels_by_number


def resolve_label_for_page_id(
    page_id: int,
    root_labels_by_number: Dict[int, str],
    page_id_to_number: Dict[int, int],
    fallback_id_labels: Dict[int, str],
) -> Optional[str]:
    number = page_id_to_number.get(page_id)
    if isinstance(number, int):
        root_label = root_labels_by_number.get(number)
        if root_label is not None:
            return root_label
    return fallback_id_labels.get(page_id)


def unique_target_path(path: Path) -> Path:
    if not path.exists():
        return path

    stem = path.stem
    suffix = path.suffix
    index = 1
    while True:
        candidate = path.with_name(f"{stem}_{index}{suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def unique_target_dir(path: Path) -> Path:
    if not path.exists():
        return path

    index = 1
    while True:
        candidate = path.with_name(f"{path.name}_{index}")
        if not candidate.exists():
            return candidate
        index += 1


def iter_assets(data: Dict[str, Any], collection: str) -> Iterable[Dict[str, Any]]:
    assets_toa = data.get("assets_toa")
    if not isinstance(assets_toa, dict):
        return []
    items = assets_toa.get(collection)
    if isinstance(items, list):
        return [x for x in items if isinstance(x, dict)]
    return []


def copy_assets(
    data: Dict[str, Any],
    source_root: Path,
    output_root: Path,
    collection: str,
) -> Tuple[int, int, int]:
    # pageId in assets points to nested page IDs.
    # Root-level pages labels (Copertina, I, II, ...) are keyed by page number.
    root_labels_by_number = collect_root_label_by_number(data)
    page_id_to_number: Dict[int, int] = {}
    collect_page_id_to_number(data, page_id_to_number)

    fallback_id_labels: Dict[int, str] = {}
    collect_page_labels(data, fallback_id_labels)

    copied = 0
    missing_source = 0
    skipped = 0

    for asset in iter_assets(data, collection):
        kernel_path = asset.get("kernel_path")
        page_id = asset.get("pageId")

        if not isinstance(kernel_path, str) or not kernel_path.strip():
            skipped += 1
            continue

        if not isinstance(page_id, int):
            skipped += 1
            continue

        label = resolve_label_for_page_id(
            page_id=page_id,
            root_labels_by_number=root_labels_by_number,
            page_id_to_number=page_id_to_number,
            fallback_id_labels=fallback_id_labels,
        )
        if label is None:
            label = "SenzaLabel"

        source_file = source_root / Path(kernel_path.replace("\\", "/"))
        if not source_file.exists() or not source_file.is_file():
            missing_source += 1
            print(f"[missing] {source_file}")
            continue

        target_dir = output_root / safe_folder_name(f"Pagina {label}")
        target_dir.mkdir(parents=True, exist_ok=True)
        # If this is an HTML package entry (typically .../index.html),
        # copy the whole package folder so referenced assets are included.
        if source_file.suffix.lower() == ".html":
            package_dir = source_file.parent
            package_name = safe_folder_name(package_dir.name or "html_package")
            target_package_dir = unique_target_dir(target_dir / package_name)
            shutil.copytree(package_dir, target_package_dir)
            copied += 1
            print(f"[copied-dir] {package_dir} -> {target_package_dir}")
            continue

        target_file = unique_target_path(target_dir / source_file.name)
        shutil.copy2(source_file, target_file)
        copied += 1
        print(f"[copied] {source_file} -> {target_file}")

    return copied, missing_source, skipped


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Copy asset files by page label using kernel_path and pageId."
        )
    )
    parser.add_argument(
        "--json",
        default="json.json",
        help="Path to the JSON file (default: json.json).",
    )
    parser.add_argument(
        "--source-root",
        required=True,
        help="Base folder where kernel_path files are located.",
    )
    parser.add_argument(
        "--output-root",
        default="assets_by_label",
        help="Destination root folder (default: assets_by_label).",
    )
    parser.add_argument(
        "--collection",
        default="containers",
        choices=["containers", "resources"],
        help="assets_toa collection to process (default: containers).",
    )
    args = parser.parse_args()

    json_path = Path(args.json)
    source_root = Path(args.source_root)
    output_root = Path(args.output_root)

    with json_path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)

    copied, missing_source, skipped = copy_assets(
        data=data,
        source_root=source_root,
        output_root=output_root,
        collection=args.collection,
    )

    print("\nDone.")
    print(f"collection: {args.collection}")
    print(f"copied: {copied}")
    print(f"missing source files: {missing_source}")
    print(f"skipped (no kernel_path/pageId/label): {skipped}")


if __name__ == "__main__":
    main()
