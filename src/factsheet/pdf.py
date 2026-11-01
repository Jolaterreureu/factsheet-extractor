import io
import textwrap

import pdfplumber

IMAGE_PAGES = 3
IMAGE_DPI = 120


def pdf_text(path, layout: bool = False, max_pages: int | None = None) -> str:
    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:max_pages]:
            text = page.extract_text(layout=layout) or ""
            if layout:
                lines = [line.rstrip() for line in text.splitlines() if line.strip()]
                text = textwrap.dedent("\n".join(lines))
            pages.append(text)
    return "\n\n".join(pages)


def page_images(path, max_pages: int = IMAGE_PAGES, dpi: int = IMAGE_DPI) -> list[bytes]:
    images = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages[:max_pages]:
            buffer = io.BytesIO()
            page.to_image(resolution=dpi).original.save(buffer, format="PNG")
            images.append(buffer.getvalue())
    return images
