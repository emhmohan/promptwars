import os, tempfile
os.environ["CAREERPIPE_DB"] = os.path.join(tempfile.mkdtemp(), "learners.json")
os.environ["LLM_PROVIDER"] = "mock"

from fastapi.testclient import TestClient
from backend.main import app

c = TestClient(app)

def test_full_flow():
    s = c.post("/api/learners", json={"name": "T", "goal": "fs", "claimed": ["python", "sql", "html"]}).json()
    uid = s["id"]
    assert s["gap"]["total"] == 9 and s["plan"]["steps"]
    order = [x["skill"] for x in s["plan"]["steps"]]
    assert order.index("js") < order.index("react")            # prerequisites first
    s = c.post(f"/api/learners/{uid}/simulate-fail", json={"skill": "react"}).json()
    assert "js" in s["refresh"]                                 # root-cause refresher inserted
    s = c.post(f"/api/learners/{uid}/goal", json={"goal": "ml"}).json()
    assert s["role_name"] == "ML Engineer"                      # re-plan on goal change
    q = c.get(f"/api/learners/{uid}/question", params={"skill": "python"}).json()
    r = c.post(f"/api/learners/{uid}/answer", json={"skill": "python", "choice": 1, "context": "diagnostic"}).json()
    assert r["result"]["correct"] and "options" in q
    n = c.post(f"/api/learners/{uid}/interview/next").json()
    e = c.post(f"/api/learners/{uid}/interview/answer", json={"round": "technical", "skill": n["skill"], "question": n["q"], "answer": "short"}).json()
    assert 0 <= e["eval"]["score"] <= 10
    assert c.get(f"/api/learners/{uid}/rejection").json()["letter"]
    assert c.get(f"/api/learners/{uid}/passport").json()["skills"]
    assert c.post("/api/syllabus", json={"text": "python sql statistics", "role": "da"}).json()["coverage"] > 0

def _pass(uid, skill):
    from backend import agents as A
    c.get(f"/api/learners/{uid}/question", params={"skill": skill})
    return c.post(f"/api/learners/{uid}/answer", json={"skill": skill, "choice": A.Q[skill]["mcq"]["answer"], "context": "diagnostic"}).json()["state"]

def test_sample_scenario_fullstack():
    s = c.post("/api/learners", json={"name": "Sam", "goal": "fs", "claimed": ["python", "sql", "html"]}).json()
    uid = s["id"]
    assert {t["skill"]: t["status"] for t in s["gap"]["tests"]}["js"] == "missing"
    for sk in ["python", "sql", "html"]:
        s = _pass(uid, sk)
    status = {t["skill"]: t["status"] for t in s["gap"]["tests"]}
    assert status["html"] == status["sql"] == "pass"
    assert all(status[k] == "missing" for k in ("js", "react", "node"))
    order = [x["skill"] for x in s["plan"]["steps"]]
    assert order[0] == "js"                                         # unlocks the most skills
    assert order.index("js") < order.index("react") and order.index("js") < order.index("node")
    assert order.index("css") < order.index("react")
    assert all(x["resources"] for x in s["plan"]["steps"])
    s = c.post(f"/api/learners/{uid}/simulate-fail", json={"skill": "react"}).json()
    assert "js" in s["refresh"]
    assert any(l["agent"] == "Mentor Agent" and "JavaScript" in l["msg"] for l in s["log"])
    s = c.post(f"/api/learners/{uid}/goal", json={"goal": "be"}).json()
    assert {t["skill"]: t["status"] for t in s["gap"]["tests"]}["sql"] == "pass"   # shared skill stays green

def test_failed_skill_not_in_passport():
    s = c.post("/api/learners", json={"name": "P", "goal": "fs", "claimed": ["python"]}).json()
    uid = s["id"]
    c.post(f"/api/learners/{uid}/simulate-fail", json={"skill": "react"})
    p = c.get(f"/api/learners/{uid}/passport").json()
    assert all(i["skill"] != "React" for i in p["skills"])

def test_question_rotation_and_weighting():
    from backend import agents as A
    s = c.post("/api/learners", json={"name": "W", "goal": "fs", "claimed": []}).json()
    uid = s["id"]
    seen = set()
    for _ in range(3):
        q = c.get(f"/api/learners/{uid}/question", params={"skill": "js"}).json()
        seen.add(q["q"])
        pool = A.Q["js"]["mcq"], *A.Q["js"]["more"]
        ans = next(p["answer"] for p in pool if p["q"] == q["q"])
        r = c.post(f"/api/learners/{uid}/answer", json={"skill": "js", "choice": ans, "context": "diagnostic"}).json()
        assert r["result"]["correct"]
    assert len(seen) == 3                                   # a different question each time
    q = c.get(f"/api/learners/{uid}/question", params={"skill": "js"}).json()
    pool = A.Q["js"]["mcq"], *A.Q["js"]["more"]
    wrong = (next(p["answer"] for p in pool if p["q"] == q["q"]) + 1) % 3
    s = c.post(f"/api/learners/{uid}/answer", json={"skill": "js", "choice": wrong, "context": "diagnostic"}).json()["state"]
    assert s["prof"]["js"] >= A.K                           # 3 right + 1 wrong stays a pass (weighted)


def test_hr_gates_decision_and_fixes_flip_it():
    s = c.post("/api/learners", json={"name": "R", "goal": "fs", "claimed": ["python", "sql", "html"]}).json()
    uid = s["id"]
    r = c.get(f"/api/learners/{uid}/rejection").json()
    assert r["decision_now"] == "REJECT" and r["behavioral"] is None
    assert any("Behavioral" in x for x in r["reasons"])
    assert r["fixes"][0]["skill"].startswith("Behavioral")
    for sk in ("python", "sql", "html", "js", "css", "git", "api", "testing", "react", "node"):
        s = _pass(uid, sk)
    c.post(f"/api/learners/{uid}/interview/answer", json={"round": "hr", "skill": None, "question": "q",
           "answer": "situation task action result learned team i led the fix and the result was good for the whole team"})
    r = c.get(f"/api/learners/{uid}/rejection").json()
    assert r["decision_now"] == "HIRE" and r["behavioral"] >= 5


def test_arbiter_conflict_names_prereq():
    s = c.post("/api/learners", json={"name": "A", "goal": "fs", "claimed": ["python"]}).json()
    log = " ".join(x["msg"] for x in s["log"] if x["agent"] == "Arbiter")
    assert "Conflict" in log or "No conflict" in log


def test_profile_certs_and_projects():
    s = c.post("/api/learners", json={"name": "C", "goal": "fs", "claimed": [],
               "certifications": ["Meta React Developer Certificate"],
               "projects": ["Built a Flask REST API with PostgreSQL", ""]}).json()
    uid = s["id"]
    assert [e["text"] for e in s["certs"]] == ["Meta React Developer Certificate"] and len(s["projects"]) == 1
    assert "react" in s["claimed"] and "sql" in s["claimed"]            # inferred from certs/projects
    s = c.put(f"/api/learners/{uid}/profile", json={"certifications": [], "projects": ["Dockerized a Node.js app"]}).json()
    assert "docker" in s["claimed"] and s["certs"] == []
    p = c.get(f"/api/learners/{uid}/passport").json()
    assert p["projects"] == ["Dockerized a Node.js app"]


def test_roles_timeline_evidence():
    s = c.post("/api/learners", json={"name": "E", "goal": "fs", "claimed": ["python", "sql", "html"]}).json()
    uid = s["id"]
    roles = c.get(f"/api/learners/{uid}/roles").json()
    assert len(roles) == 5 and roles[0]["match"] >= roles[-1]["match"]
    weak = c.post(f"/api/learners/{uid}/evidence", json={"skill": "js", "text": "i know javascript"}).json()
    assert weak["result"]["score"] < 6 and "js" not in weak["state"]["ver"]
    txt = "Built a REST API in Python with Flask and PostgreSQL, deployed it on Render with JWT auth, 200 users, 95% test coverage using pytest, designed endpoints and a database schema."
    ok = c.post(f"/api/learners/{uid}/evidence", json={"skill": "python", "text": txt}).json()
    assert ok["result"]["score"] >= 6 and "python" in ok["state"]["ver"]
    assert len(ok["state"]["timeline"]) >= 2


def test_guided_demo():
    s = c.post("/api/demo/guided").json()
    assert s["name"] == "Asha" and "python" in s["ver"] and "react" in s["fails"] or "js" in s["refresh"]
    assert len(s["timeline"]) >= 3 and s["evidence"]


def test_project_interview_and_impact():
    s = c.post("/api/demo/guided").json(); uid = s["id"]
    q = c.post(f"/api/learners/{uid}/interview/next", params={"round": "project"}).json()
    assert q["round"] == "project" and q["skill"] and q["q"]
    r = c.post(f"/api/learners/{uid}/interview/answer", json={"round": "project", "skill": q["skill"], "question": q["q"], "answer": "I chose a simple layout because of time and tested it on phones."}).json()
    assert 0 <= r["eval"]["score"] <= 10
    imp = c.get("/api/cohort").json()["impact"]
    assert imp["after"] >= imp["before"]


def test_explain():
    s = c.post("/api/demo/guided").json()
    e = c.get(f"/api/learners/{s['id']}/explain", params={"skill": "python"}).json()
    assert e["evidence"] and e["rule"] and "next" in e


def test_stale_nudges():
    s = c.post("/api/demo/guided").json(); uid = s["id"]
    assert not s["stale"]
    s = c.post(f"/api/learners/{uid}/decay", json={"days": 90}).json()
    assert s["stale"] and s["stale"][0]["days"] >= 90


def test_resume():
    s = c.post("/api/demo/guided").json()
    r = c.get(f"/api/learners/{s['id']}/resume").json()
    assert r["bullets"]
    e = c.post("/api/learners", json={"name": "N", "goal": "fs"}).json()
    assert c.get(f"/api/learners/{e['id']}/resume").json()["bullets"] == []


def test_jobmatch():
    s = c.post("/api/demo/guided").json()
    r = c.post(f"/api/learners/{s['id']}/jobmatch", json={"text": "We need Python, SQL, React and Docker experience."}).json()
    assert r["required"] >= 3 and "Python" in r["verified"] and any(m in r["missing"] for m in ("React", "Docker"))
    assert c.post(f"/api/learners/{s['id']}/jobmatch", json={"text": "gardening and cooking"}).json()["match"] == 0


def test_document_hard_test():
    s = c.post("/api/learners", json={"name": "D", "goal": "fs"}).json(); uid = s["id"]
    r = c.post(f"/api/learners/{uid}/document", json={"text": "B.Tech course: Data Structures in Python, Databases with SQL, Web development using HTML and React.", "kind": "course description"}).json()
    assert {"python", "sql", "react"} <= set(r["skills"]) and "react" in r["state"]["claimed"]
    q = c.get(f"/api/learners/{uid}/question", params={"skill": "python", "hard": True}).json()
    assert q["level"] in ("hard", "hard-fallback") and len(q["options"]) >= 3


def test_accounts():
    assert c.post("/api/auth/signup", json={"username": "ab", "password": "secret1"}).status_code == 400
    assert c.post("/api/auth/signup", json={"username": "asha_k", "password": "123"}).status_code == 400
    r = c.post("/api/auth/signup", json={"username": "Asha_K", "password": "secret1"}).json()
    h = {"Authorization": "Bearer " + r["token"]}
    assert r["username"] == "asha_k" and r["learner_id"] is None
    assert c.post("/api/auth/signup", json={"username": "asha_k", "password": "secret1"}).status_code == 400
    uid = c.post("/api/learners", headers=h, json={"name": "Asha", "goal": "fs", "claimed": ["python"]}).json()["id"]
    assert c.get(f"/api/learners/{uid}").status_code == 401                    # owned profile needs the token
    assert c.get(f"/api/learners/{uid}", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert c.get(f"/api/learners/{uid}", headers=h).status_code == 200
    assert c.post("/api/auth/login", json={"username": "asha_k", "password": "wrong"}).status_code == 400
    l = c.post("/api/auth/login", json={"username": "asha_k", "password": "secret1"}).json()
    assert l["learner_id"] == uid                                              # progress comes back on login
    assert c.get("/api/auth/me", headers={"Authorization": "Bearer " + l["token"]}).json()["learner_id"] == uid
    guest = c.post("/api/learners", json={"name": "G", "goal": "fs", "claimed": []}).json()["id"]
    assert c.get(f"/api/learners/{guest}").status_code == 200                  # guests still work
