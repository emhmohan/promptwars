"""Tiny JSON-file store for learner state (swap for Postgres later)."""
import json, os, pathlib, threading, time, uuid

_DEFAULT = pathlib.Path(__file__).parent / "data" / "learners.json"
_lock = threading.RLock()


def _db() -> pathlib.Path:
    return pathlib.Path(os.getenv("CAREERPIPE_DB") or _DEFAULT)


def _load() -> dict:
    p = _db()
    return json.loads(p.read_text()) if p.exists() else {}


def get(uid: str):
    with _lock:
        return _load().get(uid)


def save(L: dict) -> None:
    with _lock:
        db = _load()
        db[L["id"]] = L
        p = _db()
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(db, indent=1))
        os.replace(tmp, p)


def all_learners() -> list:
    with _lock:
        return list(_load().values())


def new_learner(name: str, goal: str, hours: int, claimed: list) -> dict:
    return {"id": uuid.uuid4().hex[:8], "name": name, "goal": goal, "hours": hours,
            "claimed": list(claimed), "prof": {s: 0.5 for s in claimed}, "ver": [], "verified_at": {},
            "fails": {}, "refresh": [], "pending": {}, "interviews": [], "hr": [],
            "log": [], "history": [], "plan": None, "gap": None, "created": int(time.time())}
