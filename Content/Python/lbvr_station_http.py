"""

LBVR Master / Quest station HTTP helpers (editor / PIE with Python plugin).

Matches UE5/unrealEngin5.md — Prefer /v1/station/* over legacy /v1/ue/*.

"""

from __future__ import annotations



import json

import urllib.error

import urllib.parse

import urllib.request

from typing import Any



DEFAULT_BASE = "https://sector4.teambahar.com"





def _req(method: str, url: str, token: str | None = None, body: dict | None = None) -> dict[str, Any]:

    data = None

    # Cloudflare bans default Python-urllib UA (1010). Mimic curl.

    headers = {

        "Accept": "application/json",

        "User-Agent": "Sector4-MasterPC/1.0 (curl-compatible)",

    }

    if body is not None:

        data = json.dumps(body).encode("utf-8")

        headers["Content-Type"] = "application/json"

    if token:

        headers["Authorization"] = f"Bearer {token}"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:

        with urllib.request.urlopen(request, timeout=15) as resp:

            raw = resp.read().decode("utf-8")

            return {"ok": True, "status": resp.status, "json": json.loads(raw) if raw else {}}

    except urllib.error.HTTPError as e:

        raw = e.read().decode("utf-8", errors="replace")

        try:

            payload = json.loads(raw) if raw else {}

        except json.JSONDecodeError:

            payload = {"raw": raw}

        return {"ok": False, "status": e.code, "json": payload, "error": str(e)}

    except Exception as e:  # noqa: BLE001

        return {"ok": False, "status": 0, "json": {}, "error": str(e)}





def station_auth(base_url: str, station_id: str, station_token: str) -> dict[str, Any]:

    url = f"{base_url.rstrip('/')}/v1/station/auth"

    return _req("POST", url, body={"station_id": station_id, "station_token": station_token})





def poll_session(base_url: str, access_token: str, room_index: int | None = None) -> dict[str, Any]:

    url = f"{base_url.rstrip('/')}/v1/station/session"

    if room_index is not None:

        url = f"{url}?room_index={int(room_index)}"

    return _req("GET", url, token=access_token)





def publish_lan(

    base_url: str,

    access_token: str,

    lan_ip: str,

    listen_port: int = 7777,

    game_slug: str = "outbreak",

    booking_id: str = "",

    session_code: str = "",

    status: str = "waiting",

) -> dict[str, Any]:

    url = f"{base_url.rstrip('/')}/v1/station/lan"

    body: dict[str, Any] = {

        "lan_ip": lan_ip,

        "listen_port": int(listen_port),

        "game_slug": game_slug or "outbreak",

        "status": status,

    }

    if booking_id:

        body["booking_id"] = booking_id

    if session_code:

        body["session_code"] = session_code

    return _req("POST", url, token=access_token, body=body)





def discover_lan(

    base_url: str,

    session_code: str = "",

    access_token: str | None = None,

) -> dict[str, Any]:

    """Quest: GET /v1/station/lan?session_code=… (or quest station Bearer)."""

    url = f"{base_url.rstrip('/')}/v1/station/lan"

    if session_code:

        url = f"{url}?{urllib.parse.urlencode({'session_code': session_code})}"

    return _req("GET", url, token=access_token)





def session_start(base_url: str, access_token: str, booking_id: str, connected_clients: int = 0) -> dict[str, Any]:

    url = f"{base_url.rstrip('/')}/v1/station/session/start"

    return _req(

        "POST",

        url,

        token=access_token,

        body={"booking_id": booking_id, "connected_clients": int(connected_clients)},

    )





def session_end(

    base_url: str,

    access_token: str,

    booking_id: str,

    aborted: bool = False,

    duration_seconds: int = 0,

    players: list | None = None,

    team_score: int = 0,

    game_slug: str = "outbreak",

    map_name: str = "L_XRTemplate",

) -> dict[str, Any]:

    url = f"{base_url.rstrip('/')}/v1/station/session/end"

    body: dict[str, Any] = {

        "booking_id": booking_id,

        "aborted": bool(aborted),

        "duration_seconds": int(duration_seconds),

        "players": players or [],

        "team_score": int(team_score),

        "meta": {"game_slug": game_slug or "outbreak", "map": map_name},

    }

    return _req("POST", url, token=access_token, body=body)





def session_abort(base_url: str, access_token: str, booking_id: str, reason: str = "operator_end") -> dict[str, Any]:

    url = f"{base_url.rstrip('/')}/v1/station/session/abort"

    return _req(

        "POST",

        url,

        token=access_token,

        body={"booking_id": booking_id, "reason": reason},

    )





def apply_auth_to_game_instance(gi) -> dict[str, Any]:

    """Run station auth and write AccessToken onto a live GameInstance object."""

    base = str(gi.get_editor_property("ApiBaseUrl") or DEFAULT_BASE)

    sid = str(gi.get_editor_property("StationId"))

    tok = str(gi.get_editor_property("StationToken"))

    result = station_auth(base, sid, tok)

    if result.get("ok"):

        data = result["json"].get("data") or {}

        token = data.get("access_token") or ""

        gi.set_editor_property("AccessToken", token)

        result["access_token_set"] = bool(token)

        result["play_allowed"] = data.get("play_allowed", True)

    return result


