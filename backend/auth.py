"""Optional accounts: salted PBKDF2 password hashes + random bearer tokens, stored beside the learner DB."""
import hashlib, hmac, json, os, re, secrets, threading, time

from . import store

_lock = threading.RLock()
TOKEN_DAYS = 30


def _path():
    p = store._db()
    return p.with_name(p.stem + "_users.json")


def _load():
    p = _path()
    return json.loads(p.read_text()) if p.exists() else {"users": {}, "tokens": {}}


def _save(d):
    p = _path(); tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, indent=1)); os.replace(tmp, p)


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()


def _issue(d, u):
    tok = secrets.token_urlsafe(32)
    now = time.time()
    d["tokens"] = {t: v for t, v in d["tokens"].items() if now - v["t"] < TOKEN_DAYS * 86400}
    d["tokens"][tok] = {"u": u, "t": now}
    return tok


def signup(username, password):
    u = (username or "").strip().lower()
    if not re.fullmatch(r"[a-z0-9_.-]{3,32}", u):
        raise ValueError("Username: 3-32 letters, numbers, . _ -")
    if len(password or "") < 6:
        raise ValueError("Password must be at least 6 characters")
    with _lock:
        d = _load()
        if u in d["users"]: raise ValueError("That username is taken")
        salt = secrets.token_bytes(16)
        d["users"][u] = {"salt": salt.hex(), "hash": _hash(password, salt), "learner": None, "created": int(time.time())}
        tok = _issue(d, u); _save(d)
    return tok, u, None


def login(username, password):
    u = (username or "").strip().lower()
    with _lock:
        d = _load(); rec = d["users"].get(u)
        salt = bytes.fromhex(rec["salt"]) if rec else b"\0" * 16
        ok = hmac.compare_digest(_hash(password or "", salt), rec["hash"] if rec else "x")
        if not rec or not ok: raise ValueError("Wrong username or password")
        tok = _issue(d, u); _save(d)
    return tok, u, rec["learner"]


def user_for(token):
    if not token: return None
    v = _load()["tokens"].get(token)
    return v["u"] if v and time.time() - v["t"] < TOKEN_DAYS * 86400 else None


def learner_of(username):
    rec = _load()["users"].get(username)
    return rec["learner"] if rec else None


def link(username, learner_id):
    with _lock:
        d = _load()
        if username in d["users"]:
            d["users"][username]["learner"] = learner_id; _save(d)


def logout(token):
    with _lock:
        d = _load()
        if d["tokens"].pop(token, None): _save(d)
