"""Event-driven orchestrator: routes events to agents and logs every handoff."""
import time, math
from . import agents as A, store


def log(L, agent, msg):
    L["log"].append({"agent": agent, "msg": msg, "t": int(time.time())})
    L["log"] = L["log"][-80:]


def replan(L, reason):
    log(L, "Orchestrator", f"Trigger: {reason}. Convening agents.")
    gap = A.GapAnalyst().run(L)
    log(L, "Gap Analyst", f"{gap['passing']}/{gap['total']} role tests passing, {gap['match']}% match. Gaps: " +
        (", ".join(A.nm(s) for s in gap["gaps"]) or "none") + ".")
    res = A.Council().run(L, gap)
    for agent, msg in res["debate"]:
        log(L, agent, msg)
    plan = A.Curriculum().attach(L, res["plan"])
    log(L, "Curriculum Agent", f"Attached resources to {len(plan)} steps, formats adapted to your struggles.")
    L.setdefault("timeline", []).append({"t": int(time.time()), "match": gap["match"], "why": reason[:60]})
    L["timeline"] = L["timeline"][-60:]
    L["gap"], L["plan"] = gap, {"steps": plan, "total_weeks": res["total_weeks"], "summary": res["summary"]}
    store.save(L)
    return L


def _entries(lines):
    out = []
    for t in lines or []:
        t = t.strip()
        if t: out.append({"text": t[:200], "skills": A.ProfileAgent().parse(t)})
    return out


def onboard(name, goal, hours, claimed, resume_text="", certs=None, projects=None):
    certs, projects = _entries(certs), _entries(projects)
    extra = set(A.ProfileAgent().parse(resume_text))
    for e in certs + projects: extra |= set(e["skills"])
    L = store.new_learner(name, goal, hours, sorted(set(claimed) | extra))
    L["certs"], L["projects"] = certs, projects
    log(L, "Profile Agent", f"Profile built for {name}: {len(L['claimed'])} claimed skills, {len(certs)} certification(s), {len(projects)} project(s)" +
        (f" ({len(extra)} skills found in resume, certifications and projects)." if extra else "."))
    return replan(L, "profile created")


def update_profile(L, certs, projects):
    L["certs"], L["projects"] = _entries(certs), _entries(projects)
    new = {s for e in L["certs"] + L["projects"] for s in e["skills"]} - set(L["claimed"])
    for s in new:
        L["claimed"].append(s); L["prof"].setdefault(s, 0.5)
    log(L, "Profile Agent", f"Profile updated: {len(L['certs'])} certification(s), {len(L['projects'])} project(s)" +
        (". New claimed skills to verify: " + ", ".join(A.nm(s) for s in sorted(new)) if new else "."))
    return replan(L, "profile updated")


def from_document(L, text, kind):
    L["doc"] = (text or "")[:4000]
    skills = A.ProfileAgent().parse(text)
    new = [k for k in skills if k not in L["claimed"]]
    for k in new:
        L["claimed"].append(k); L["prof"].setdefault(k, 0.5)
    log(L, "Profile Agent", f"Read a {kind}: found {len(skills)} skill(s) ({', '.join(A.nm(k) for k in skills) or 'none'}); {len(new)} new claim(s) to test with hard questions.")
    replan(L, f"{kind} analysed")
    return skills


def answer(L, skill, choice, context):
    r = A.AssessmentAgent().grade(L, skill, choice)
    L["history"].append({"t": int(time.time()), "event": context, "skill": skill, "ok": r["correct"]})
    if r["correct"]:
        log(L, "Progress Agent", f"{A.nm(skill)} verified (passed {context}).")
        if skill in L["refresh"]: L["refresh"].remove(skill)
        replan(L, f"{context} passed: {A.nm(skill)}")
    elif L["prof"].get(skill, 0) >= A.K:
        log(L, "Progress Agent", f"{A.nm(skill)}: one question missed, but weighted evidence ({int(L['prof'][skill] * 100)}%) still passes.")
        replan(L, f"{context}: {A.nm(skill)} partial miss")
    else:
        fail(L, skill, context)
    return r


def fail(L, skill, context="quiz"):
    msg = A.Mentor().on_fail(L, skill)
    log(L, "Mentor Agent", msg)
    replan(L, f"{context} failed: {A.nm(skill)}")


def set_goal(L, goal):
    L["goal"] = goal
    return replan(L, "goal changed to " + A.ROLES[goal]["name"])


def set_hours(L, hours):
    L["hours"] = max(1, int(hours))
    return replan(L, f"weekly hours changed to {L['hours']}")


def interview_answer(L, round_, skill, question, ans):
    ev = A.Evaluator().score(L, round_, skill, question, ans)
    if round_ == "hr":
        L["hr"].append(ev["score"])
        log(L, "Behavioral Coach", f"HR answer scored {ev['score']}/10 (STAR structure check). Behavioral average {sum(L['hr']) / len(L['hr']):.1f}/10 now gates the hire decision.")
        store.save(L)
        return ev
    L["interviews"].append({"skill": skill, "score": ev["score"], "t": int(time.time())})
    L["prof"][skill] = A.AssessmentAgent().blend(L, skill)
    log(L, "Evaluator Agent", f"{A.nm(skill)} interview answer: {ev['score']}/10. Proficiency now {int(L['prof'][skill] * 100)}%.")
    if ev["score"] < 5:
        log(L, "Mentor Agent", f"Weak interview answer on {A.nm(skill)}. Re-planning with extra practice.")
        L["fails"][skill] = L["fails"].get(skill, 0) + 1
    replan(L, f"interview result: {A.nm(skill)} {ev['score']}/10")
    return ev


def decay(L, days):
    f = 0.5 ** (days / 120.0)  # half-life of 120 days without refresh
    for s in L["ver"]:
        L["prof"][s] = round(L["prof"].get(s, 0) * f, 2)
    for k in list(L.get("verified_at", {})): L["verified_at"][k] -= days * 86400
    log(L, "Progress Agent", f"Simulated {days} days without practice: verified skills decayed.")
    return replan(L, f"skill decay after {days} days")


def evidence(L, skill, text):
    r = A.EvidenceAgent().score(L, skill, text)
    ok = r["score"] >= 6
    L.setdefault("evidence", []).append({"skill": skill, "score": r["score"], "ok": ok, "text": text[:300], "t": int(time.time())})
    if ok:
        L["prof"][skill] = max(L["prof"].get(skill, 0), 0.62)
        if skill not in L["ver"]: L["ver"].append(skill)
        L["verified_at"][skill] = time.time()
    log(L, "Evidence Agent", f"Project evidence for {A.nm(skill)} scored {r['score']}/10" + (": accepted as proof." if ok else ": not enough to verify. Take the quiz or add detail."))
    replan(L, f"project evidence: {A.nm(skill)} {r['score']}/10")
    return r


def explain(L, skill):
    quiz = L.get("quiz", {}).get(skill, [])
    iv = [i["score"] for i in L["interviews"] if i["skill"] == skill][-3:]
    evs = [e for e in L.get("evidence", []) if e["skill"] == skill]
    prof = L["prof"].get(skill, 0)
    parts = []
    if quiz: parts.append(f"Quiz: last {len(quiz)} answer(s) {''.join('Y' if a else 'N' for a in quiz)}, newer answers weigh more.")
    if iv: parts.append(f"Interview: last {len(iv)} score(s) {', '.join(str(x) for x in iv)} out of 10.")
    if evs: parts.append(f"Project evidence: {evs[-1]['score']}/10" + (" (accepted, floors proficiency at 62%)." if evs[-1]["ok"] else " (not accepted)."))
    rule = "Blend: 40% quiz + 60% interview when both exist; otherwise whichever exists." if quiz and iv else            "Only one kind of evidence so far: add the other (quiz or interview) to firm it up." if parts else "No evidence yet: this is only a claim."
    age = int((time.time() - L["verified_at"][skill]) / 86400) if skill in L.get("verified_at", {}) else None
    return {"key": skill, "skill": A.nm(skill), "score": round(prof, 2), "passes": prof >= A.K, "threshold": A.K, "evidence": parts, "rule": rule,
            "days_since_verified": age, "next": "Passing." if prof >= A.K else f"Needs {int((A.K - prof) * 100) + 1} more points: take a quiz or interview on {A.nm(skill)}."}


def stale(L, days=30):
    out = []
    for sk in L["ver"]:
        t = L.get("verified_at", {}).get(sk)
        if t is None: continue
        d = int((time.time() - t) / 86400)
        if d >= days or L["prof"].get(sk, 0) < A.K:
            out.append({"skill": sk, "name": A.nm(sk), "days": d, "score": round(L["prof"].get(sk, 0), 2),
                        "projected": round(L["prof"].get(sk, 0) * 0.5 ** (60 / 120.0), 2)})
    return sorted(out, key=lambda x: x["score"])


def passport(L):
    items, pending = [], []
    for s in L["ver"]:
        ev = [f"Quiz: {'passed' if h['ok'] else 'failed'}" for h in L["history"] if h["skill"] == s][-2:]
        ev += [f"Interview: {i['score']}/10" for i in L["interviews"] if i["skill"] == s][-2:]
        ev += [f"Project evidence: {e['score']}/10" for e in L.get("evidence", []) if e["skill"] == s][-1:]
        passed = any(h["ok"] for h in L["history"] if h["skill"] == s) or any(i["score"] >= 5 for i in L["interviews"] if i["skill"] == s) or any(e["ok"] for e in L.get("evidence", []) if e["skill"] == s)
        if not passed:
            pending.append(A.nm(s)); continue
        items.append({"skill": A.nm(s), "score": round(L["prof"].get(s, 0), 2), "verified": L["prof"].get(s, 0) >= A.K, "evidence": ev})
    return {"name": L["name"], "goal": A.ROLES[L["goal"]]["name"], "match": (L.get("gap") or {}).get("match"), "skills": items, "not_yet_verified": pending,
            "behavioral": round(sum(L["hr"]) / len(L["hr"]), 1) if L["hr"] else None,
            "certs": [e["text"] for e in L.get("certs", [])], "projects": [e["text"] for e in L.get("projects", [])],
            "note": "Scores are estimates from short quizzes and interview answers, not formal certification."}


def snapshot(L):
    d = {k: L[k] for k in ("id", "name", "goal", "hours", "claimed", "prof", "ver", "fails", "refresh", "interviews", "hr", "gap", "plan")}
    d["roles"], d["timeline"] = A.GapAnalyst().all_roles(L), L.get("timeline", [])
    d["certs"], d["projects"] = L.get("certs", []), L.get("projects", [])
    d["evidence"] = L.get("evidence", [])[-10:]
    d["stale"] = stale(L)
    d["log"] = L["log"][-40:]; d["history"] = L["history"][-30:]; d["role_name"] = A.ROLES[L["goal"]]["name"]
    return d
