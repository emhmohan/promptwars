"""LLM provider layer. Every agent works WITHOUT an LLM (deterministic fallback),
so the demo never breaks. Set LLM_PROVIDER in .env to enable real model calls."""
import json, os, re, time
import requests

TIMEOUT = 45


def provider() -> str:
    return os.getenv("LLM_PROVIDER", "mock").strip().lower()


def available() -> bool:
    return provider() != "mock"


def status() -> dict:
    p = provider()
    keyed = {"gemini": "GEMINI_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY",
             "groq": "GROQ_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
    has_key = True if p in ("mock", "ollama") else bool(os.getenv(keyed.get(p, ""), ""))
    return {"provider": p, "ready": has_key, "model": _model(p)}


def _model(p):
    return {"gemini": os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            "openai": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "anthropic": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5-5"),
            "ollama": os.getenv("OLLAMA_MODEL", "llama3.1"),
            "groq": os.getenv("GROQ_MODEL", "openai/gpt-oss-20b"),
            "openrouter": os.getenv("OPENROUTER_MODEL", "meta-llama/llama-3.3-70b-instruct:free")}.get(p, "rule-based")


def _post(url, **kw):
    """POST with backoff on 429 (free-tier rate limits) and 5xx."""
    for i in range(4):
        r = requests.post(url, **kw)
        if r.status_code not in (429, 500, 502, 503) or i == 3:
            return r
        try: wait = float(r.headers.get("retry-after", 0))
        except ValueError: wait = 0
        time.sleep(min(max(wait, 1.5 * (i + 1)), 10))
    return r


COMPAT = {"groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
          "openrouter": ("https://openrouter.ai/api/v1", "OPENROUTER_API_KEY")}


def _call(p: str, system: str, user: str, as_json: bool) -> str:
    if p == "gemini":
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{_model(p)}:generateContent"
        body = {"systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}]}
        if as_json:
            body["generationConfig"] = {"responseMimeType": "application/json"}
        r = requests.post(url, params={"key": os.environ["GEMINI_API_KEY"]}, json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    if p == "openai":
        body = {"model": _model(p), "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if as_json:
            body["response_format"] = {"type": "json_object"}
        r = requests.post("https://api.openai.com/v1/chat/completions",
                          headers={"Authorization": "Bearer " + os.environ["OPENAI_API_KEY"]}, json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    if p in COMPAT:
        base, keyenv = COMPAT[p]
        body = {"model": _model(p), "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if "gpt-oss" in _model(p):
            body["reasoning_effort"] = "low"
        if as_json and p == "groq":
            body["response_format"] = {"type": "json_object"}
        r = _post(base + "/chat/completions", headers={"Authorization": "Bearer " + os.environ[keyenv]},
                          json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    if p == "anthropic":
        body = {"model": _model(p), "max_tokens": 1024, "system": system, "messages": [{"role": "user", "content": user}]}
        r = requests.post("https://api.anthropic.com/v1/messages",
                          headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"], "anthropic-version": "2023-06-01"},
                          json=body, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()["content"][0]["text"]
    if p == "ollama":
        body = {"model": _model(p), "stream": False,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if as_json:
            body["format"] = "json"
        r = requests.post(os.getenv("OLLAMA_URL", "http://localhost:11434") + "/api/chat", json=body, timeout=120)
        r.raise_for_status()
        return r.json()["message"]["content"]
    raise ValueError("unknown provider " + p)


def complete_json(system: str, user: str, fallback):
    """Ask the LLM for JSON. Returns `fallback` on any problem."""
    if not available():
        return fallback
    try:
        sysj = system + "\nReturn ONLY valid JSON, no markdown. Escape newlines inside strings as \\n."
        try:
            text = _call(provider(), sysj, user, True)
        except requests.HTTPError as e:
            if e.response is None or e.response.status_code != 400: raise
            text = _call(provider(), sysj, user, False)  # strict JSON mode rejected the output; parse it ourselves
        m = re.search(r"\{.*\}", text, re.S)
        return json.loads(m.group(0) if m else text)
    except Exception as e:  # network, quota, bad key, bad JSON
        print("[llm] fallback used:", repr(e)[:160])
        return fallback


def complete_text(system: str, user: str, fallback: str) -> str:
    if not available():
        return fallback
    try:
        return _call(provider(), system, user, False).strip() or fallback
    except Exception as e:
        print("[llm] fallback used:", repr(e)[:160])
        return fallback
