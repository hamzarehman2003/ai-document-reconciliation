"""Generate the demo dataset.

Usage (from the project root):
    venv/Scripts/python -m scripts.generate_dataset --sets 50 --seed 42
"""

import argparse
import json
import random
import shutil
from collections import Counter
from pathlib import Path

from faker import Faker

from scripts.generate_dataset.models import DocType, DocumentSet
from scripts.generate_dataset.render_pdf import (
    render_goods_receipt,
    render_invoice,
    render_purchase_order,
)
from scripts.generate_dataset.scan import make_scanned_copy
from scripts.generate_dataset.scenarios import generate_sets
from scripts.generate_dataset.vendors import (
    build_buyer,
    build_receiving_staff,
    build_vendors,
)

DEFAULT_OUTPUT = Path("data/generated")
TEST_SHARE = 0.3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sets", type=int, default=50, help="number of document sets")
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument(
        "--out", type=Path, default=DEFAULT_OUTPUT, help="output folder"
    )
    parser.add_argument(
        "--scan-ratio",
        type=float,
        default=0.3,
        help="share of documents saved as scans (0 to 1)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    fake = Faker("en_GB")
    fake.seed_instance(args.seed)
    document_sets = generate_sets(
        args.sets,
        random.Random(args.seed),
        build_buyer(fake),
        build_vendors(fake),
        build_receiving_staff(fake),
    )

    sets_folder = args.out / "sets"
    if sets_folder.exists():
        shutil.rmtree(sets_folder)

    # Separate random generators, so changing the scan ratio or split
    # never changes the documents themselves.
    scan_rng = random.Random(args.seed + 1)
    test_ids = choose_test_sets(document_sets, random.Random(args.seed + 2))

    manifest = []
    for document_set in document_sets:
        split = "test" if document_set.set_id in test_ids else "train"
        manifest += write_set(document_set, args.out, scan_rng, args.scan_ratio, split)

    manifest_path = args.out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print_summary(document_sets, manifest, test_ids, args.out)


def choose_test_sets(document_sets: list[DocumentSet], rng: random.Random) -> set[str]:
    """Hold back ~30% of whole sets for testing extraction accuracy later."""
    set_ids = [document_set.set_id for document_set in document_sets]
    rng.shuffle(set_ids)
    return set(set_ids[: round(len(set_ids) * TEST_SHARE)])


def write_set(
    document_set: DocumentSet,
    output: Path,
    scan_rng: random.Random,
    scan_ratio: float,
    split: str,
) -> list[dict[str, object]]:
    """Write the three PDFs and truth.json for one set; return manifest entries."""
    folder = output / "sets" / document_set.set_id
    folder.mkdir(parents=True)
    (folder / "truth.json").write_text(
        document_set.model_dump_json(indent=2), encoding="utf-8"
    )

    order = document_set.purchase_order
    receipt = document_set.goods_receipt
    invoice = document_set.invoice
    documents = [
        (DocType.PURCHASE_ORDER, order.number, order.vendor.vendor_id),
        (DocType.GOODS_RECEIPT, receipt.number, receipt.vendor.vendor_id),
        (DocType.INVOICE, invoice.number, invoice.vendor.vendor_id),
    ]

    entries = []
    for doc_type, number, vendor_id in documents:
        path = folder / f"{number}.pdf"
        match doc_type:
            case DocType.PURCHASE_ORDER:
                render_purchase_order(order, path)
            case DocType.GOODS_RECEIPT:
                render_goods_receipt(receipt, path)
            case DocType.INVOICE:
                render_invoice(invoice, path)

        scanned = scan_rng.random() < scan_ratio
        if scanned:
            scan_path = folder / f"{number}_scan.pdf"
            make_scanned_copy(path, scan_path, scan_rng)
            path.unlink()
            path = scan_path

        entries.append(
            {
                "file": path.relative_to(output).as_posix(),
                "set_id": document_set.set_id,
                "doc_type": doc_type.value,
                "number": number,
                "vendor_id": vendor_id,
                "scanned": scanned,
                "split": split,
            }
        )
    return entries


def print_summary(
    document_sets: list[DocumentSet],
    manifest: list[dict[str, object]],
    test_ids: set[str],
    output: Path,
) -> None:
    scanned = sum(1 for entry in manifest if entry["scanned"])
    print(
        f"Generated {len(document_sets)} sets ({len(manifest)} documents, "
        f"{scanned} scanned) in {output}"
    )
    print("Scenarios:")
    counts = Counter(document_set.scenario for document_set in document_sets)
    for scenario, count in sorted(counts.items()):
        print(f"  {scenario.value:<22} {count}")
    train_count = len(document_sets) - len(test_ids)
    print(f"Split: {train_count} train sets, {len(test_ids)} test sets")


if __name__ == "__main__":
    main()
