from services.assistent_service import _escape_template_literals


def test_escape_template_literals_doubles_curly_braces():
    raw = '{"title": "MacBook", "price": 999}'
    escaped = _escape_template_literals(raw)
    assert escaped == '{{"title": "MacBook", "price": 999}}'


def test_escape_template_literals_preserves_plain_text():
    text = "Brand: Apple\nModel: MacBook Air"
    assert _escape_template_literals(text) == text
