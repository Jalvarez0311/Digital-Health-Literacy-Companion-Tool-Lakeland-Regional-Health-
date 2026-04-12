import os
from pathlib import Path

import boto3
from botocore.config import Config
from dotenv import load_dotenv
from tomllib import load

load_dotenv(Path(__file__).resolve().parents[3] / ".env")


def _build_simple_pdf(text: str) -> bytes:
    """
    Build a styled PDF from LLM-generated markdown discharge text using reportlab.

    Recognised markdown constructs:
      - ``---`` on its own line  → horizontal rule + heading-detection trigger
      - ``**bold**``             → inline bold via XML markup
      - ``- item``               → bullet list item
      - ``1. item``              → numbered list item
      - first non-empty, non-list line after ``---`` → section / title heading
      - blank line               → small vertical spacer
      - everything else          → body paragraph
    """
    import io
    import re
    from html import escape as _he

    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

    # ------------------------------------------------------------------
    # Inline-bold helper: split on **…**, HTML-escape plain parts, wrap
    # bold parts in <b>…</b> so reportlab's XML parser handles them.
    # ------------------------------------------------------------------
    def _inline(s: str) -> str:
        parts = re.split(r"\*\*(.+?)\*\*", s)
        return "".join(
            _he(p) if i % 2 == 0 else f"<b>{_he(p)}</b>" for i, p in enumerate(parts)
        )

    # ------------------------------------------------------------------
    # Paragraph styles
    # ------------------------------------------------------------------
    style_title = ParagraphStyle(
        "DischargeTitle",
        fontName="Helvetica-Bold",
        fontSize=15,
        textColor=HexColor("#000000"),
        leading=19,
        spaceAfter=6,
        alignment=TA_LEFT,
    )
    style_section = ParagraphStyle(
        "DischargeSection",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=HexColor("#000000"),
        leading=14,
        spaceBefore=6,
        spaceAfter=4,
        alignment=TA_LEFT,
    )
    style_body = ParagraphStyle(
        "DischargeBody",
        fontName="Helvetica",
        fontSize=10,
        textColor=HexColor("#000000"),
        leading=14,
        spaceAfter=4,
        alignment=TA_LEFT,
    )
    style_list = ParagraphStyle(
        "DischargeList",
        fontName="Helvetica",
        fontSize=10,
        textColor=HexColor("#000000"),
        leading=14,
        leftIndent=16,
        spaceAfter=3,
        alignment=TA_LEFT,
    )

    # ------------------------------------------------------------------
    # Document setup – letter page, 1-inch margins on all sides
    # ------------------------------------------------------------------
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=inch,
        rightMargin=inch,
        topMargin=inch,
        bottomMargin=inch,
    )

    # ------------------------------------------------------------------
    # Normalise Unicode typographic characters that Helvetica / WinAnsiEncoding
    # cannot render (they appear as black boxes in the PDF viewer).
    # ------------------------------------------------------------------
    def _normalize(s: str) -> str:
        return (
            s.replace("\u2014", "-")   # em dash
             .replace("\u2013", "-")   # en dash
             .replace("\u2012", "-")   # figure dash
             .replace("\u2010", "-")   # hyphen
             .replace("\u2011", "-")   # non-breaking hyphen
             .replace("\u2018", "'")   # left single quotation mark
             .replace("\u2019", "'")   # right single quotation mark
             .replace("\u201c", '"')   # left double quotation mark
             .replace("\u201d", '"')   # right double quotation mark
             .replace("\u2026", "...")  # ellipsis
             .replace("\u00a0", " ")   # non-breaking space
        )

    # ------------------------------------------------------------------
    # Parse lines into reportlab flowables
    # ------------------------------------------------------------------
    story = []
    lines = _normalize(text or "").splitlines()

    # expect_heading: True after a --- divider; preserved across blank lines
    # and list items; consumed on the first non-empty, non-list line.
    expect_heading: bool = False
    is_first_heading: bool = True  # first heading → Title style; rest → Section

    _bullet_re = re.compile(r"^- (.+)$")
    _numbered_re = re.compile(r"^(\d+)\. (.+)$")

    for line in lines:
        stripped = line.rstrip()

        # ---- horizontal rule / section divider ----
        if stripped == "---":
            story.append(Spacer(1, 4))
            story.append(
                HRFlowable(width="100%", thickness=0.75, color=HexColor("#CCCCCC"))
            )
            story.append(Spacer(1, 4))
            expect_heading = True
            continue

        # ---- blank line ----
        if stripped == "":
            story.append(Spacer(1, 5))
            # expect_heading is intentionally preserved here
            continue

        # ---- bullet list item: "- text" ----
        bullet_m = _bullet_re.match(stripped)
        if bullet_m:
            content = bullet_m.group(1)
            story.append(Paragraph(f"\u2022 {_inline(content)}", style_list))
            # expect_heading is intentionally preserved here
            continue

        # ---- numbered list item: "N. text" ----
        numbered_m = _numbered_re.match(stripped)
        if numbered_m:
            num = numbered_m.group(1)
            content = numbered_m.group(2)
            story.append(Paragraph(f"{num}. {_inline(content)}", style_list))
            # expect_heading is intentionally preserved here
            continue

        # ---- heading or body paragraph ----
        if expect_heading:
            if is_first_heading:
                story.append(Paragraph(_inline(stripped), style_title))
                is_first_heading = False
            else:
                story.append(Paragraph(_inline(stripped), style_section))
            expect_heading = False
        else:
            story.append(Paragraph(_inline(stripped), style_body))

    doc.build(story)
    return buffer.getvalue()


def upload_discharge_pdf_to_s3(
    *, patient_id: int, document_id: int, document_text: str
) -> tuple[str, str]:
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
        config=Config(signature_version="s3v4"),
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


def _s3_client():
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
    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(signature_version="s3v4"),
    ), bucket_name


def fetch_discharge_pdf_from_s3(*, object_key: str) -> bytes:
    s3, bucket_name = _s3_client()
    response = s3.get_object(Bucket=bucket_name, Key=object_key)
    return response["Body"].read()


def discharge_pdf_bytes(*, s3_object_key: str | None, document_text: str) -> bytes:
    if s3_object_key:
        try:
            return fetch_discharge_pdf_from_s3(object_key=s3_object_key)
        except Exception:
            pass
    return _build_simple_pdf(document_text)


def get_presigned_s3_url(*, object_key: str, expires_in_seconds: int = 900) -> str:
    """
    Create a time-limited URL for embedding/downloading a private PDF from S3.
    """
    s3, bucket_name = _s3_client()
    return s3.generate_presigned_url(
        ClientMethod="get_object",
        Params={"Bucket": bucket_name, "Key": object_key},
        ExpiresIn=expires_in_seconds,
    )
