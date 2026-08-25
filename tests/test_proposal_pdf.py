import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from routers.proposal import _render_pdf, _sanitize_latin1


def test_render_pdf_returns_pdf_bytes():
    pdf_bytes = _render_pdf("Proposal for Acme Corp\n\nBudget: $5,000\nTimeline: 2 weeks")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_pdf_handles_empty_content():
    pdf_bytes = _render_pdf("")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_render_pdf_handles_smart_punctuation():
    # Test with smart quotes, em-dash, ellipsis, and bullet
    # These characters are outside Latin-1 and would cause encoding errors without sanitization
    content = 'Client said "great" — let\'s proceed\n• Budget: $5,000\n… More details'
    pdf_bytes = _render_pdf(content)
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")


def test_sanitize_latin1_converts_smart_quotes_and_apostrophes():
    text = (
        "Client\u2019s brief: \u201cship fast\u201d \u2014 we\u2019ll deliver\u2026"
    )
    result = _sanitize_latin1(text)
    assert result == "Client's brief: \"ship fast\" - we'll deliver..."
    assert "?" not in result
