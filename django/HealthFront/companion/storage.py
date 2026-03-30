import os

import boto3


def _build_simple_pdf(text: str) -> bytes:
    """
    Build a small, plain-text PDF without external PDF libraries.
    Supports basic multi-page text rendering.
    """

    def _escape_pdf_text(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    lines = (text or "").splitlines() or [""]
    lines_per_page = 44
    pages = [lines[i:i + lines_per_page] for i in range(0, len(lines), lines_per_page)]

    objects = []

    # 1: catalog, 2: pages container
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")

    kids = []
    page_obj_numbers = []
    content_obj_numbers = []

    next_obj = 3
    for _ in pages:
        page_obj_numbers.append(next_obj)
        next_obj += 1
        content_obj_numbers.append(next_obj)
        next_obj += 1

    for page_no, page_lines in enumerate(pages):
        page_obj = page_obj_numbers[page_no]
        content_obj = content_obj_numbers[page_no]
        kids.append(f"{page_obj} 0 R")

        content_lines = [
            "BT",
            "/F1 11 Tf",
            "50 780 Td",
            "14 TL",
        ]

        first = True
        for raw in page_lines:
            safe = _escape_pdf_text(raw)
            if first:
                content_lines.append(f"({safe}) Tj")
                first = False
            else:
                content_lines.append(f"T* ({safe}) Tj")
        content_lines.append("ET")

        content = "\n".join(content_lines).encode("utf-8")
        page_dict = (
            "<< /Type /Page /Parent 2 0 R "
            "/MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> "
            f"/Contents {content_obj} 0 R >>"
        )

        objects.append(page_dict)
        objects.append(f"<< /Length {len(content)} >>\nstream\n{content.decode('utf-8')}\nendstream")

    pages_dict = f"<< /Type /Pages /Count {len(pages)} /Kids [{' '.join(kids)}] >>"
    objects.insert(1, pages_dict)

    # Build final PDF with xref
    pdf_parts = [b"%PDF-1.4\n"]
    offsets = [0]

    for idx, obj in enumerate(objects, start=1):
        offsets.append(sum(len(p) for p in pdf_parts))
        pdf_parts.append(f"{idx} 0 obj\n{obj}\nendobj\n".encode("utf-8"))

    xref_start = sum(len(p) for p in pdf_parts)
    xref_lines = [f"xref\n0 {len(objects) + 1}\n", "0000000000 65535 f \n"]
    for off in offsets[1:]:
        xref_lines.append(f"{off:010d} 00000 n \n")

    trailer = (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_start}\n%%EOF\n"
    )

    pdf_parts.append("".join(xref_lines).encode("utf-8"))
    pdf_parts.append(trailer.encode("utf-8"))
    return b"".join(pdf_parts)


def upload_discharge_pdf_to_s3(*, patient_id: int, document_id: int, document_text: str) -> tuple[str, str]:
    """
    Upload a generated discharge document as PDF to S3-compatible storage.
    Returns (object_key, object_url).
    """
    

    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    bucket_name = os.getenv("S3_BUCKET_NAME")
    access_key = os.getenv("S3_ACCESS_KEY_ID")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    region = os.getenv("S3_REGION", "us-east-1")

    if not all([endpoint_url, bucket_name, access_key, secret_key]):
        raise ValueError(
            "Missing S3 env vars. Required: "
            "S3_ENDPOINT_URL, S3_BUCKET_NAME, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY."
        )

    object_key = f"{patient_id}/{document_id}.pdf"
    pdf_bytes = _build_simple_pdf(document_text)

    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )
    s3.put_object(
        Bucket=bucket_name,
        Key=object_key,
        Body=pdf_bytes,
        ContentType="application/pdf",
    )

    base = endpoint_url.rstrip("/")
    object_url = f"{base}/{bucket_name}/{object_key}"
    return object_key, object_url
