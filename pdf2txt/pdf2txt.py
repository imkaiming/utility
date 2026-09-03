import pymupdf
from pathlib import Path

def pdf_to_text(pdf_path: str, txt_name: str = "output.txt") -> None:
    script_dir = Path(__file__).parent.resolve()


    txt_path = script_dir / txt_name

    doc = pymupdf.open(pdf_path)

    text = "\n\n".join(page.get_text() for page in doc)

    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(text)

    doc.close()
    print(f"Done -> {txt_path}")

if __name__ == "__main__":
    import sys
    pdf = sys.argv[1] if len(sys.argv) > 1 else "input.pdf"
    out = sys.argv[2] if len(sys.argv) > 2 else "output.txt"
    pdf_to_text(pdf, out)