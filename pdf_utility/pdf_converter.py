#!/usr/bin/env python3
"""Convert PDF files to extracted text or per-page JPEG images."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import pymupdf
except ImportError as exc:
    raise SystemExit(
        "PyMuPDF is required. Install it with: python -m pip install PyMuPDF"
    ) from exc


def convert_to_text(document: pymupdf.Document, output_path: Path, force: bool) -> None:
    if output_path.exists() and not force:
        raise FileExistsError(f"Output already exists: {output_path} (use --force to replace it)")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n\n".join(page.get_text() for page in document)
    output_path.write_text(text, encoding="utf-8")
    print(f"Wrote text: {output_path}")


def convert_to_jpeg(
    document: pymupdf.Document,
    output_dir: Path,
    input_path: Path,
    dpi: int,
    force: bool,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    stem = input_path.stem
    output_paths = [
        output_dir / f"{stem}_page_{page_number:03}.jpg"
        for page_number in range(1, document.page_count + 1)
    ]

    existing = [path for path in output_paths if path.exists()]
    if existing and not force:
        raise FileExistsError(
            f"Output already exists: {existing[0]} (use --force to replace existing images)"
        )

    scale = dpi / 72
    matrix = pymupdf.Matrix(scale, scale)
    for page, output_path in zip(document, output_paths):
        pixmap = page.get_pixmap(matrix=matrix, alpha=False, colorspace=pymupdf.csRGB)
        pixmap.save(output_path, jpg_quality=90)

    print(f"Wrote {len(output_paths)} JPEG page(s) to: {output_dir}")


def natural_sort_key(path: Path) -> tuple[tuple[int, int | str], ...]:
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in re.split(r"(\d+)", path.name)
    )


def convert_images_to_pdf(input_path: Path, output_path: Path, force: bool) -> None:
    supported_extensions = {".jpg", ".jpeg"}
    if input_path.is_file():
        if input_path.suffix.casefold() not in supported_extensions:
            raise ValueError("Input must be a .jpg or .jpeg image when type is 'pdf'.")
        image_paths = [input_path]
    elif input_path.is_dir():
        image_paths = sorted(
            (
                path
                for path in input_path.iterdir()
                if path.is_file() and path.suffix.casefold() in supported_extensions
            ),
            key=natural_sort_key,
        )
        if not image_paths:
            raise ValueError(f"No .jpg or .jpeg images found in: {input_path}")
    else:
        raise FileNotFoundError(f"Input image or directory not found: {input_path}")

    if output_path.suffix.casefold() != ".pdf":
        raise ValueError("Output path must have a .pdf extension when type is 'pdf'.")
    if output_path.exists() and not force:
        raise FileExistsError(
            f"Output already exists: {output_path} (use --force to replace it)"
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with pymupdf.open() as output_document:
        for image_path in image_paths:
            with pymupdf.open(image_path) as image_document:
                image_pdf = pymupdf.open("pdf", image_document.convert_to_pdf())
                try:
                    output_document.insert_pdf(image_pdf)
                finally:
                    image_pdf.close()
        output_document.save(output_path)

    print(f"Wrote {len(image_paths)} page(s): {output_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convert PDF to text/JPEG, or JPG/JPEG images to a PDF. "
            "For type 'pdf', input may be one image or a directory of images."
        )
    )
    parser.add_argument(
        "input",
        type=Path,
        help="PDF file for txt/jpg; JPG/JPEG file or directory for pdf",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="Output .txt file, JPEG directory, or .pdf file according to type",
    )
    parser.add_argument(
        "type", choices=("txt", "jpg", "jpeg", "pdf"), help="Output type"
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="JPEG render resolution in dots per inch (default: 150)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing output files",
    )
    args = parser.parse_args()
    if args.dpi < 1:
        parser.error("--dpi must be a positive integer")
    return args


def main() -> int:
    args = parse_args()
    input_path = args.input.expanduser()
    output_path = args.output.expanduser()

    try:
        if args.type == "pdf":
            convert_images_to_pdf(input_path, output_path, args.force)
            return 0

        if not input_path.is_file():
            print(f"Error: input PDF not found: {input_path}", file=sys.stderr)
            return 2

        with pymupdf.open(input_path) as document:
            if args.type == "txt":
                convert_to_text(document, output_path, args.force)
            else:
                convert_to_jpeg(
                    document,
                    output_path,
                    input_path,
                    args.dpi,
                    args.force,
                )
    except (pymupdf.FileDataError, pymupdf.PasswordError) as exc:
        print(f"Error: could not open input file: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
