"""Tiny JSON-file store for learner state (swap for Postgres later). Reads are cached until the file changes."""
import copy, json, os, pathlib, threading, time, uuid

_DEFAULT = pathlib.Path(__file__).parent / "data" / "learners.json"
_lock = threading.RLock()
_cache = {"key": None, "data": {}}


def _db() -> pathlib.Path:
    return pathlib.Path(os.getenv("CAREERPIPE_DB") or _DEFAULT)


def _key(p: pathlib.Path):
    st = p.stat()
    return (str(p), st.st_mtime_ns, st.st_size)


def _load() -> dict:
    """Parsed DB, re-read only when the file's mtime/size changed. Callers must not mutate the result."""
    p = _db()
    if not p.exists():
        return {}
    k = _key(p)
    if _cache["key"] != k:
        _cache["data"] = json.loads(p.read_text()); _cache["key"] = k
    return _cache["data"]


def get(uid: str):
    with _lock:
        return copy.deepcopy(_load().get(uid))


def save(L: dict) -> None:
    with _lock:
        db = dict(_load())
        db[L["id"]] = copy.deepcopy(L)
        p = _db()
        tmp = p.with_suffix(".tmp")
        tmp.write_text(json.dumps(db, separators=(",", ":")))
        os.replace(tmp, p)
        _cache["data"] = db; _cache["key"] = _key(p)


def all_learners() -> list:
    with _lock:
        return copy.deepcopy(list(_load().values()))


def new_learner(name: str, goal: str, hours: int, claimed: list) -> dict:
    return {"id": uuid.uuid4().hex[:8], "name": name, "goal": goal, "hours": hours,
            "claimed": list(claimed), "prof": {s: 0.5 for s in claimed}, "ver": [], "verified_at": {},
            "fails": {}, "refresh": [], "pending": {}, "interviews": [], "hr": [],
            "log": [], "history": [], "plan": None, "gap": None, "created": int(time.time())}
