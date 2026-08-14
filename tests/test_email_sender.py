from pathlib import Path

import pytest
from PIL import Image

import email_sender
from email_sender import _normalise_lists, _logo_html, md_to_pdf, send_email


# ── _normalise_lists ─────────────────────────────────────────────────────

def test_normalise_lists_splits_inline_bullets():
    text = "Intro - first point - second point"
    result = _normalise_lists(text)
    lines = result.splitlines()
    assert lines[0] == "Intro"
    assert "- first point" in lines
    assert "- second point" in lines


def test_normalise_lists_leaves_headings_alone():
    text = "### A heading - with a dash"
    assert _normalise_lists(text) == text


def test_normalise_lists_leaves_normal_lines_alone():
    text = "Just a normal sentence."
    assert _normalise_lists(text) == text


# ── _logo_html / md_to_pdf ───────────────────────────────────────────────

def test_logo_html_falls_back_to_wordmark_when_missing(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGO_PATH", str(tmp_path / "does_not_exist.png"))
    html = _logo_html()
    assert "REDACTED_BRAND" in html
    assert "<img" not in html


def test_logo_html_embeds_image_when_present(monkeypatch, tmp_path):
    logo_path = tmp_path / "logo.png"
    Image.new("RGBA", (40, 20), (0, 153, 204, 255)).save(logo_path)
    monkeypatch.setenv("LOGO_PATH", str(logo_path))

    html = _logo_html()
    assert "<img" in html
    assert "data:image/png;base64," in html


def test_md_to_pdf_produces_valid_pdf(monkeypatch, tmp_path):
    monkeypatch.setenv("LOGO_PATH", str(tmp_path / "does_not_exist.png"))
    output_path = tmp_path / "out.pdf"

    ok = md_to_pdf("# Heading\n\n- one\n- two", output_path, date_label="14 Aug 2026")

    assert ok is True
    assert output_path.exists()
    assert output_path.read_bytes()[:5] == b"%PDF-"


# ── send_email TLS gating (fix from earlier session: only skip cert
#    verification for loopback hosts, never for a remote SMTP host) ───────

class _FakeSMTP:
    instances = []

    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.starttls_context = None
        self.sent_messages = []
        _FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.starttls_context = context

    def login(self, user, password):
        pass

    def send_message(self, msg):
        self.sent_messages.append(msg)


@pytest.fixture
def fake_smtp(monkeypatch, tmp_path):
    _FakeSMTP.instances = []
    monkeypatch.setattr(email_sender.smtplib, "SMTP", _FakeSMTP)
    pdf_path = tmp_path / "digest.pdf"
    pdf_path.write_bytes(b"%PDF-fake")
    return pdf_path


def test_loopback_host_skips_cert_verification(fake_smtp):
    send_email("127.0.0.1", 1025, "user", "pass", "to@example.com",
               "subject", "body", fake_smtp)
    ctx = _FakeSMTP.instances[0].starttls_context
    assert ctx.verify_mode.name == "CERT_NONE"
    assert ctx.check_hostname is False


def test_localhost_hostname_skips_cert_verification(fake_smtp):
    send_email("localhost", 1025, "user", "pass", "to@example.com",
               "subject", "body", fake_smtp)
    ctx = _FakeSMTP.instances[0].starttls_context
    assert ctx.verify_mode.name == "CERT_NONE"


def test_remote_host_keeps_full_cert_verification(fake_smtp):
    send_email("smtp.gmail.com", 587, "user", "pass", "to@example.com",
               "subject", "body", fake_smtp)
    ctx = _FakeSMTP.instances[0].starttls_context
    assert ctx.verify_mode.name != "CERT_NONE"
    assert ctx.check_hostname is True


def test_sends_one_message_per_recipient(fake_smtp):
    send_email("127.0.0.1", 1025, "user", "pass", "a@example.com, b@example.com",
               "subject", "body", fake_smtp)
    # one SMTP session, but send_message called once per recipient inside it,
    # each addressed only to that recipient (never a shared To: header)
    session = _FakeSMTP.instances[0]
    assert len(session.sent_messages) == 2
    assert {msg["To"] for msg in session.sent_messages} == {"a@example.com", "b@example.com"}
