import argparse
import hashlib
import io
import re

import httpx
from azure.identity import DefaultAzureCredential
from azure.storage.blob import ContainerClient
from pypdf import PdfReader, PdfWriter

PDF = "https://www.boe.es/buscar/pdf/1995/BOE-A-1995-25444-consolidado.pdf"
MAX_CHARS = 400_000
HEADING = re.compile(r"^(?:LIBRO [IVX]+|TÍTULO (?:PRELIMINAR|[IVXL]+(?: BIS)?))$", re.MULTILINE)


def split(pdf: bytes) -> list[tuple[bytes, range, int]]:
    reader = PdfReader(io.BytesIO(pdf))
    texts = [page.extract_text() for page in reader.pages]
    starts = [i for i, text in enumerate(texts) if HEADING.search(text)]
    cuts, size = [starts[0]], 0
    for start, end in zip(starts, [*starts[1:], len(texts)], strict=True):
        section = sum(len(text) for text in texts[start:end])
        if size + section > MAX_CHARS:
            cuts, size = [*cuts, start], 0
        size += section
    parts = []
    for pages in (range(start, end) for start, end in zip(cuts, [*cuts[1:], len(texts)], strict=True)):
        writer, out = PdfWriter(), io.BytesIO()
        for page in pages:
            writer.add_page(reader.pages[page])
        writer.write(out)
        parts.append((out.getvalue(), pages, sum(len(texts[page]) for page in pages)))
    return parts


def upload(account_url: str, pdf: bytes) -> str:
    digest = hashlib.sha256(pdf).hexdigest()
    container = ContainerClient(account_url, "corpus", credential=DefaultAzureCredential())
    current = {blob.name: (blob.metadata or {}).get("sha256") for blob in container.list_blobs(include=["metadata"])}
    if current and set(current.values()) == {digest}:
        return f"corpus unchanged, sha256 {digest[:12]}"
    parts, names = split(pdf), list[str]()
    for number, (part, pages, chars) in enumerate(parts, start=1):
        if chars >= MAX_CHARS:
            raise ValueError(f"part {number} has {chars} characters")
        names.append(name := f"code-part-{number}.pdf")
        container.upload_blob(name, part, overwrite=True, metadata={"sha256": digest})
        print(f"{name}: pages {pages.start + 1}-{pages.stop}, {chars} characters")
    for stale in set(current) - set(names):
        container.delete_blob(stale)
    return f"uploaded {len(parts)} parts, sha256 {digest[:12]}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Split the consolidated Criminal Code PDF and upload its parts.")
    parser.add_argument("--account-url", required=True)
    pdf = httpx.get(PDF, timeout=120, follow_redirects=True).raise_for_status().content
    print(upload(parser.parse_args().account_url, pdf))


if __name__ == "__main__":
    main()
