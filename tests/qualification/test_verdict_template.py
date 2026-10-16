from pathlib import Path


def test_verdict_template_has_review_gate_and_never_authorizes_install():
    text = Path("docs/qualification/VERDICT-template.md").read_text(encoding="utf-8")

    lower = text.lower()
    for marker in ("qualified", "blocked", "inconclusive", "ordinary-turn", "quota-independence", "next gate"):
        assert marker in lower
    assert "installable: false" in text
    assert "installable: true" not in text
