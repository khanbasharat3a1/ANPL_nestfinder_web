from app.services.pagination import create_cursor_token, parse_cursor_token

SECRET = "super-secret-key-12345"


def test_cursor_token_roundtrip():
    token = create_cursor_token(
        doc_id="listing_99",
        sort_field="createdAt",
        sort_value="2026-10-12T10:00:00Z",
        secret_key=SECRET,
    )
    assert token and "." in token

    decoded = parse_cursor_token(token, SECRET)
    assert decoded is not None
    assert decoded["id"] == "listing_99"
    assert decoded["field"] == "createdAt"
    assert decoded["val"] == "2026-10-12T10:00:00Z"


def test_cursor_token_tampered():
    token = create_cursor_token(
        doc_id="listing_99",
        sort_field="createdAt",
        sort_value=12345,
        secret_key=SECRET,
    )
    tampered = token[:-4] + "abcd"
    assert parse_cursor_token(tampered, SECRET) is None
    assert parse_cursor_token("invalid.token", SECRET) is None
    assert parse_cursor_token("", SECRET) is None
    assert parse_cursor_token(None, SECRET) is None


def test_cursor_token_wrong_secret():
    token = create_cursor_token(
        doc_id="listing_99",
        sort_field="rentPerMonth",
        sort_value=4500,
        secret_key=SECRET,
    )
    assert parse_cursor_token(token, "wrong-secret-key") is None
