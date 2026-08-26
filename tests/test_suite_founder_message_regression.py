from pathlib import Path


TEMPLATE = Path(__file__).resolve().parents[1] / "templates" / "suite_landing.html"
LINKEDIN_URL = "https://www.linkedin.com/in/gerald-jerry-ross-2340855/"
LINKEDIN_ANCHOR = (
    '<a href="https://www.linkedin.com/in/gerald-jerry-ross-2340855/" '
    'target="_blank" rel="noopener noreferrer">Gerald "Jerry" Ross on LinkedIn</a>'
)


def test_founder_message_identity_and_link_safety():
    source = TEMPLATE.read_text(encoding="utf-8")
    forbidden = "ala" + "dyr"
    assert forbidden not in source.lower()
    assert LINKEDIN_URL in source
    assert LINKEDIN_ANCHOR in source
