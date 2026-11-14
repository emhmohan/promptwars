"""FastAPI app. Run from project root:  uvicorn backend.main:app --reload"""
import pathlib
from dotenv import load_dotenv
load_dotenv(pathlib.Path(__file__).resolve().parent.parent / ".env")

import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from fastapi.middleware.gzip import GZipMiddleware
from typing import List, Optional

from . import agents as A, auth, llm, orchestrator as O, store

app = FastAPI(title="CareerPipe Career CI/CD", docs_url=None, redoc_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1024)
_LRN = re.compile(r"^/api/learners/([0-9a-f]{8})(?:/|$)")


def bearer(request: Request):
    h = request.headers.get("authorization", "")
    return h[7:] if h.startswith("Bearer ") else ""


@app.middleware("http")
async def guard(request: Request, call_next):
    """A learner that belongs to an account can only be opened with that account's token. Guests/demo learners stay open."""
    m = _LRN.match(request.url.path)
    if m:
        L = store.get(m.group(1))
        if L and L.get("owner") and auth.user_for(bearer(request)) != L["owner"]:
            return JSONResponse({"detail": "Sign in to the account that owns this profile."}, status_code=401)
    return await call_next(request)


@app.middleware("http")
async def headers(request: Request, call_next):
    r = await call_next(request)
    r.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "public, max-age=300"
    r.headers.update({"X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "no-referrer",
                      "Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; img-src 'self' data:; frame-ancestors 'none'"})
    return r


def claim(request: Request, L):
    u = auth.user_for(bearer(request))
    if u:
        L["owner"] = u; store.save(L); auth.link(u, L["id"])
    return L


class Cred(BaseModel):
    username: str = Field(max_length=32)
    password: str = Field(max_length=128)


def need(uid):
    L = store.get(uid)
    if not L: raise HTTPException(404, "learner not found")
    return L


class NewLearner(BaseModel):
    name: str = Field(max_length=60)
    goal: str = "fs"
    hours: int = Field(8, ge=1, le=80)
    claimed: List[str] = Field([], max_length=40)
    resume_text: str = Field("", max_length=20000)
    certifications: List[str] = Field([], max_length=30)
    projects: List[str] = Field([], max_length=30)

class Profile(BaseModel):
    certifications: List[str] = Field([], max_length=30)
    projects: List[str] = Field([], max_length=30)

class Choice(BaseModel):
    skill: str
    choice: int
    context: str = "quiz"

class Goal(BaseModel): goal: str
class Hours(BaseModel): hours: int
class Skill(BaseModel): skill: str
class Msg(BaseModel): message: str = Field(max_length=2000)
class Days(BaseModel): days: int = 60
class IAnswer(BaseModel):
    round: str = "technical"
    skill: Optional[str] = None
    question: str = Field(max_length=2000)
    answer: str = Field(max_length=6000)
class Ev(BaseModel):
    skill: str
    text: str = Field(max_length=6000)
class JD(BaseModel): text: str = Field(max_length=20000)
class Doc(BaseModel):
    text: str = Field(max_length=20000)
    kind: str = "resume"
class Syl(BaseModel):
    text: str = Field(max_length=20000)
    role: str = "fs"


@app.get("/api/status")
def status(): return llm.status()

@app.get("/api/meta")
def meta():
    return {"skills": {k: {"name": v["name"], "prereqs": v["prereqs"]} for k, v in A.SK.items()},
            "roles": {k: {"name": v["name"], "skills": v["skills"]} for k, v in A.ROLES.items()}}

@app.get("/api/learners")
def learners(): return [{"id": L["id"], "name": L["name"], "goal": L["goal"]} for L in store.all_learners()]

@app.post("/api/auth/signup")
def signup(b: Cred):
    try: tok, u, lid = auth.signup(b.username, b.password)
    except ValueError as e: raise HTTPException(400, str(e))
    return {"token": tok, "username": u, "learner_id": lid}

@app.post("/api/auth/login")
def login(b: Cred, request: Request):
    key = f"{request.client.host if request.client else '?'}|{b.username.strip().lower()}"
    if auth.throttled(key): raise HTTPException(429, "Too many failed attempts. Wait a few minutes and try again.")
    try: tok, u, lid = auth.login(b.username, b.password)
    except ValueError as e:
        auth.note_fail(key); raise HTTPException(400, str(e))
    auth.clear_fails(key)
    return {"token": tok, "username": u, "learner_id": lid}

@app.get("/api/auth/me")
def me(request: Request):
    u = auth.user_for(bearer(request))
    if not u: raise HTTPException(401, "not signed in")
    return {"username": u, "learner_id": auth.learner_of(u)}

@app.post("/api/auth/logout")
def logout(request: Request):
    auth.logout(bearer(request)); return {"ok": True}

@app.post("/api/learners")
def create(b: NewLearner, request: Request):
    if b.goal not in A.ROLES: raise HTTPException(400, "unknown role")
    L = O.onboard(b.name, b.goal, b.hours, [s for s in b.claimed if s in A.SK], b.resume_text, b.certifications, b.projects)
    return O.snapshot(claim(request, L))

@app.put("/api/learners/{uid}/profile")
def profile(uid: str, b: Profile): return O.snapshot(O.update_profile(need(uid), b.certifications, b.projects))

@app.get("/api/learners/{uid}")
def get(uid: str): return O.snapshot(need(uid))

@app.post("/api/learners/{uid}/goal")
def goal(uid: str, b: Goal):
    if b.goal not in A.ROLES: raise HTTPException(400, "unknown role")
    return O.snapshot(O.set_goal(need(uid), b.goal))

@app.post("/api/learners/{uid}/hours")
def hours(uid: str, b: Hours): return O.snapshot(O.set_hours(need(uid), b.hours))

@app.get("/api/learners/{uid}/question")
def question(uid: str, skill: str, fresh: bool = False, hard: bool = False):
    L = need(uid)
    if skill not in A.SK: raise HTTPException(400, "unknown skill")
    q = A.AssessmentAgent().question(L, skill, fresh, hard); store.save(L); return q

@app.post("/api/learners/{uid}/answer")
def answer(uid: str, b: Choice):
    L = need(uid); r = O.answer(L, b.skill, b.choice, b.context)
    return {"result": r, "state": O.snapshot(L)}

@app.post("/api/learners/{uid}/simulate-fail")
def sim_fail(uid: str, b: Skill):
    L = need(uid); O.fail(L, b.skill, "simulated quiz"); return O.snapshot(L)

@app.post("/api/learners/{uid}/interview/next")
def inext(uid: str, round: str = "technical", skill: Optional[str] = None):
    L = need(uid); O.log(L, "Interviewer Agent", f"Preparing a {round} question."); store.save(L)
    return A.Interviewer().question(L, round, skill)

@app.post("/api/learners/{uid}/interview/answer")
def ianswer(uid: str, b: IAnswer):
    L = need(uid); ev = O.interview_answer(L, b.round, b.skill, b.question, b.answer)
    return {"eval": ev, "state": O.snapshot(L)}

@app.get("/api/learners/{uid}/rejection")
def rejection(uid: str):
    L = need(uid); r = A.Recruiter().rejection(L, L["gap"]); O.log(L, "Recruiter Agent", "Wrote an honest rejection review."); store.save(L); return r

@app.get("/api/learners/{uid}/roles")
def roles(uid: str): return A.GapAnalyst().all_roles(need(uid))

@app.post("/api/learners/{uid}/evidence")
def evidence(uid: str, b: Ev):
    L = need(uid)
    if b.skill not in A.SK: raise HTTPException(400, "unknown skill")
    r = O.evidence(L, b.skill, b.text); return {"result": r, "state": O.snapshot(L)}

@app.get("/api/learners/{uid}/explain")
def explain(uid: str, skill: str):
    if skill not in A.SK: raise HTTPException(400, "unknown skill")
    return O.explain(need(uid), skill)

@app.post("/api/learners/{uid}/document")
def document(uid: str, b: Doc):
    L = need(uid); skills = O.from_document(L, b.text, b.kind if b.kind in ("resume", "course description", "job description") else "document")
    return {"skills": skills, "state": O.snapshot(L)}

@app.post("/api/learners/{uid}/jobmatch")
def jobmatch(uid: str, b: JD):
    L = need(uid); r = A.JobMatcher().match(L, b.text)
    O.log(L, "Job Match Agent", f"Compared a job posting: {r['match']}% covered by verified skills."); store.save(L); return r

@app.get("/api/learners/{uid}/resume")
def resume(uid: str):
    L = need(uid); pp = O.passport(L); b = A.ResumeAgent().bullets(L, pp)
    O.log(L, "Resume Agent", f"Wrote {len(b)} resume bullet(s) from verified evidence only."); store.save(L)
    return {"bullets": b, "note": "Built only from verified skills, accepted project evidence and listed certifications."}

@app.get("/api/learners/{uid}/passport")
def passport(uid: str): return O.passport(need(uid))

@app.post("/api/learners/{uid}/decay")
def decay(uid: str, b: Days): return O.snapshot(O.decay(need(uid), b.days))

@app.post("/api/learners/{uid}/mentor")
def mentor(uid: str, b: Msg):
    L = need(uid); r = A.Mentor().chat(L, b.message); O.log(L, "Mentor Agent", "Answered a learner question."); store.save(L); return {"reply": r}

@app.get("/api/cohort")
def cohort(): return A.CohortAnalyst().report(store.all_learners())

@app.post("/api/syllabus")
def syllabus(b: Syl):
    if b.role not in A.ROLES: raise HTTPException(400, "unknown role")
    return A.CohortAnalyst().syllabus(b.text, b.role)

@app.post("/api/demo/guided")
def guided(request: Request):
    """One-click replay of the story: onboard, verify, fail React (root-cause re-plan), add project evidence."""
    L = O.onboard("Asha", "fs", 8, ["python", "sql", "html"],
                  "", ["Meta Front-End Developer certificate"], ["Built a Python script that loads SQL data into a dashboard"])
    for sk in ("python", "sql"):
        q = A.AssessmentAgent().question(L, sk); pool = A.AssessmentAgent().pool(sk)
        O.answer(L, sk, next((p["answer"] for p in pool if p["q"] == q["q"]), pool[0]["answer"]), "diagnostic")
    O.fail(L, "react", "guided demo: simulated quiz failure")
    O.evidence(L, "html", "Built a responsive portfolio site in HTML and CSS, deployed on GitHub Pages, tested layouts at 3 breakpoints, designed accessible forms, 120 visitors.")
    return O.snapshot(claim(request, L))

@app.post("/api/demo/seed")
def seed():
    # (name, goal, claimed, skills to verify with a correct quiz answer)
    samples = [("Asha", "fs", ["python", "sql", "html"], ["python", "sql", "html"]),
               ("Ravi", "fs", ["html", "css", "js"], ["html", "css", "js", "git"]),
               ("Meena", "ml", ["python", "stats"], ["python"]),
               ("Karthik", "da", ["sql", "python"], ["sql", "python", "stats"]),
               ("Divya", "genai", ["python", "api", "git"], ["python", "api"]),
               ("Arun", "be", ["python", "git"], [])]
    existing = {l["name"] for l in store.all_learners()}
    for n, g, c, verify in samples:
        if n in existing: continue
        L = O.onboard(n, g, 8, c)
        for sk in verify:
            q = A.AssessmentAgent().question(L, sk)
            pool = A.AssessmentAgent().pool(sk)
            ans = next((p["answer"] for p in pool if p["q"] == q["q"]), pool[0]["answer"])
            O.answer(L, sk, ans, "diagnostic")
    return cohort()

app.mount("/", StaticFiles(directory=str(pathlib.Path(__file__).resolve().parent.parent / "frontend"), html=True), name="ui")
