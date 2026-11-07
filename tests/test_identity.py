from fastapi import FastAPI, Response
from fastapi.testclient import TestClient

from app.auth.dependencies import get_identity
from app.auth.identity import Identity, resolve_identity


def test_user_header_wins():
    class Req:
        headers = {"X-User-Id": "  42 ", "X-Guest-Session-Id": "g1"}
        cookies = {}

    resp = Response()
    ident = resolve_identity(Req(), resp)
    assert ident.is_user
    assert ident.external_user_id == "42"
    assert ident.guest_session_id is None


def test_guest_from_header():
    class Req:
        headers = {"X-Guest-Session-Id": "abc"}
        cookies = {}

    resp = Response()
    ident = resolve_identity(Req(), resp)
    assert ident.is_guest
    assert ident.guest_session_id == "abc"


def test_guest_from_cookie():
    class Req:
        headers = {}
        cookies = {"bb_guest_session": "from-cookie"}

    resp = Response()
    ident = resolve_identity(Req(), resp)
    assert ident.is_guest
    assert ident.guest_session_id == "from-cookie"


def test_new_guest_generated():
    class Req:
        headers = {}
        cookies = {}

    resp = Response()
    ident = resolve_identity(Req(), resp)
    assert ident.is_guest
    assert ident.guest_session_id
    assert len(ident.guest_session_id) >= 16
