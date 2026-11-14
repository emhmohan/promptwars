"""Specialised agents. Each has ONE job, takes the shared learner state `L`,
and returns structured output. Deterministic core + optional LLM enrichment."""
import json, math, pathlib, random, time
from . import llm

_D = pathlib.Path(__file__).parent / "data"
SK = json.loads((_D / "skills.json").read_text())["skills"]
ROLES = json.loads((_D / "skills.json").read_text())["roles"]
Q = json.loads((_D / "questions.json").read_text())
K = 0.6  # a skill "passes" at or above this proficiency
HR_QS = ["Tell me about a time you faced a difficult bug or deadline. What did you do?",
         "Describe a project you are proud of and your exact role in it.",
         "Tell me about a time you worked in a team and disagreed. How did it end?"]
HR_KW = ["situation", "task", "action", "result", "learned", "team", "i "]


def known(L, s): return L["prof"].get(s, 0) >= K
def nm(s): return SK[s]["name"]
def weeks(L, s): return max(1, math.ceil(SK[s]["weeks"] * 8 / max(1, L["hours"])))


def ancestors(s, acc=None):
    acc = acc if acc is not None else set()
    for p in SK[s]["prereqs"]:
        if p not in acc:
            acc.add(p); ancestors(p, acc)
    return acc


# ---------------------------------------------------------------- Profile
class ProfileAgent:
    name = "Profile Agent"

    def parse(self, text: str) -> list:
        t = (text or "").lower()
        return [s for s, v in SK.items() if any(a in t for a in v["aliases"])]


# ------------------------------------------------------------- Assessment
class AssessmentAgent:
    name = "Assessment Agent"

    def pool(self, skill):
        return [Q[skill]["mcq"]] + Q[skill].get("more", [])

    def question(self, L, skill, fresh=False, hard=False):
        pool = self.pool(skill)
        n = L.setdefault("asked", {}).get(skill, 0)
        q = pool[n % len(pool)]
        L["asked"][skill] = n + 1
        if hard:
            doc = L.get("doc", "")[:1200]
            sysmsg = ("You write HARD multiple-choice questions for a skills test. Not definitions: use a realistic scenario, a code snippet to read, or a bug to diagnose, "
                      "where all 4 options are plausible and exactly one is correct. If a document is given, base the scenario on what the candidate claims in it. "
                      "JSON: {\"q\":str,\"options\":[4 strings],\"answer\":int index}.")
            usr = f"Skill: {nm(skill)}. Document: {doc or 'none'}. Must differ from: {q['q']}"
            g = None
            for _ in range(3):
                if not llm.available(): break
                g = llm.complete_json(sysmsg, usr, None)
                if isinstance(g, dict) and isinstance(g.get("options"), list) and len(g["options"]) >= 3 and isinstance(g.get("answer"), int) and 0 <= g["answer"] < len(g["options"]) and g.get("q"): break
                g = None
            if isinstance(g, dict) and isinstance(g.get("options"), list) and len(g["options"]) >= 3                     and isinstance(g.get("answer"), int) and 0 <= g["answer"] < len(g["options"]) and g.get("q"):
                g["hard"] = True
                L["pending"][skill] = g
                return {"skill": skill, "q": g["q"], "options": g["options"], "level": "hard"}
            q = dict(pool[-1]); L["pending"][skill] = q
            return {"skill": skill, "q": q["q"], "options": q["options"], "level": "hard-fallback"}
        if fresh and llm.available():
            g = llm.complete_json("Write ONE multiple-choice question. JSON: {\"q\":str,\"options\":[3 strings],\"answer\":int index}.",
                                  f"Skill: {nm(skill)}. Must differ from: {q['q']}", None)
            if isinstance(g, dict) and isinstance(g.get("options"), list) and len(g["options"]) >= 2 \
                    and isinstance(g.get("answer"), int) and 0 <= g["answer"] < len(g["options"]) and g.get("q"):
                q = g
        L["pending"][skill] = q
        return {"skill": skill, "q": q["q"], "options": q["options"]}

    def grade(self, L, skill, choice):
        q = L["pending"].pop(skill, None) or Q[skill]["mcq"]
        ok = int(choice) == q["answer"]
        ev = L.setdefault("quiz", {}).setdefault(skill, [])
        ev.append(1 if ok else 0)
        if ok and q.get("hard"): ev.append(1)  # a correct hard answer counts double
        del ev[:-5]
        L["prof"][skill] = self.blend(L, skill)
        if skill not in L["ver"]:
            L["ver"].append(skill)
        L["verified_at"][skill] = time.time()
        return {"correct": ok, "answer": q["answer"], "score": L["prof"][skill]}

    def blend(self, L, skill):
        """Weighted evidence: recent quiz accuracy (40%) and interview answers (60%)."""
        ev = L.get("quiz", {}).get(skill, [])
        w = list(range(1, len(ev) + 1))  # newer answers weigh more
        quiz = 0.35 + 0.5 * sum(a * b for a, b in zip(ev, w)) / sum(w) if ev else None
        iv = [i["score"] for i in L["interviews"] if i["skill"] == skill][-3:]
        ivp = sum(iv) / len(iv) / 10 if iv else None
        if quiz is not None and ivp is not None:
            return round(0.4 * quiz + 0.6 * ivp, 2)
        return round(quiz if quiz is not None else ivp or 0, 2)


# ------------------------------------------------------------ Gap Analyst
class GapAnalyst:
    name = "Gap Analyst"

    def run(self, L):
        req = ROLES[L["goal"]]["skills"]; tests = []
        for s in req:
            v = L["prof"].get(s, 0)
            if v >= K: st = "pass"
            elif v > 0: st = "weak" if s in L["ver"] else "unverified"
            else: st = "missing"
            tests.append({"skill": s, "name": nm(s), "score": round(v, 2), "status": st})
        match = round(100 * sum(min(L["prof"].get(s, 0), .85) / .85 for s in req) / len(req))
        return {"tests": tests, "passing": sum(t["status"] == "pass" for t in tests), "total": len(req),
                "match": match, "gaps": [t["skill"] for t in tests if t["status"] != "pass"]}


    def all_roles(self, L):
        out = []
        for rk, r in ROLES.items():
            req = r["skills"]
            match = round(100 * sum(min(L["prof"].get(s, 0), .85) / .85 for s in req) / len(req))
            have = [nm(s) for s in req if known(L, s)]
            miss = sorted((s for s in req if not known(L, s)), key=lambda s: -unlocks(s, req))
            out.append({"role": rk, "name": r["name"], "match": match, "passing": len(have), "total": len(req),
                        "top_gaps": [nm(s) for s in miss[:3]], "current": rk == L["goal"]})
        return sorted(out, key=lambda x: -x["match"])


# ---------------------------------------------------------------- Council
def unlocks(s, req):
    return sum(1 for r in req if r != s and s in ancestors(r))


class Strategist:
    name = "Career Strategist"
    def propose(self, L, gaps):  # skills that unlock the most others first, then shortest
        req = ROLES[L["goal"]]["skills"]
        return sorted(gaps, key=lambda s: (-unlocks(s, req), SK[s]["weeks"]))

class Pedagogy:
    name = "Pedagogy Agent"
    def propose(self, L, targets):  # prerequisites first (topological)
        out, seen = [], set()
        def v(s):
            if s in seen: return
            seen.add(s)
            for p in SK[s]["prereqs"]: v(p)
            if not known(L, s): out.append(s)
        for t in targets: v(t)
        return out

class TimeBudget:
    name = "Time Budget Agent"
    def propose(self, L, order):
        t, sched = 0, []
        for s in order:
            w = weeks(L, s); sched.append({"skill": s, "start": t, "weeks": w}); t += w
        return sched, t

class Council:
    """Strategist + Pedagogy + Time Budget propose; Arbiter reconciles and explains."""
    def run(self, L, gap):
        req = ROLES[L["goal"]]["skills"]
        strat = Strategist().propose(L, gap["gaps"])
        ped = Pedagogy().propose(L, req)
        need, done, order = set(ped), set(), []
        while len(order) < len(ped):  # dependency-safe order, Strategist priority among ready skills
            ready = [s for s in ped if s not in done and all(p in done or p not in need for p in SK[s]["prereqs"])]
            s = min(ready, key=lambda x: (-unlocks(x, req), SK[x]["weeks"], ped.index(x)))
            order.append(s); done.add(s)
        sched, total = TimeBudget().propose(L, order)
        debate = []
        if strat:
            debate.append(("Career Strategist", "Fastest route to hireable: " + ", ".join(f"{nm(s)} (unlocks {unlocks(s, req)})" if unlocks(s, req) else nm(s) for s in strat[:3]) + " first."))
        pre = [s for s in ped if s not in req]
        debate.append(("Pedagogy Agent", ("Blocking issue: need foundations " + ", ".join(nm(s) for s in pre) + " before dependent skills.") if pre else "Dependency order is sound; no extra foundations needed."))
        debate.append(("Time Budget Agent", f"At {L['hours']} h/week the full path is about {total} weeks."))
        blocked = {s: [p for p in ped if p in ancestors(s)] for s in strat[:3] if s in ped}
        conflicts = [s for s, p in blocked.items() if p]
        if conflicts:
            c = conflicts[0]
            debate.append(("Arbiter", "Conflict: Strategist wants " + nm(c) + " early, but Pedagogy needs " + ", ".join(nm(p) for p in blocked[c]) + " first. Pedagogy wins; hireability matters less than a broken foundation."))
        else:
            debate.append(("Arbiter", f"No conflict. Plan fixed: {len(ped)} steps, {gap['match']}% match."))
        if order:
            debate.append(("Arbiter", "Merged order: " + " → ".join(nm(s) for s in order[:5]) + (" …" if len(order) > 5 else "") + "."))
        facts = json.dumps({"role": ROLES[L["goal"]]["name"], "order": [nm(s) for s in order], "weeks": total, "match": gap["match"]})
        summary = llm.complete_text("You are the Arbiter of a career-mentor agent council. In 2 sentences explain the roadmap to the learner, plainly.", facts,
                                    f"Your roadmap has {len(ped)} steps to reach {ROLES[L['goal']]['name']}, about {total} weeks at {L['hours']} h/week.")
        plan = []
        for it in sched:
            s = it["skill"]
            need = next((r for r in req if s in ancestors(r)), None)
            plan.append({"skill": s, "name": nm(s), "start": it["start"], "weeks": it["weeks"], "score": round(L["prof"].get(s, 0), 2),
                         "why": ("Required for " + ROLES[L["goal"]]["name"]) if s in req else f"Prerequisite of {nm(need)}" if need else "Foundation",
                         "refresher": s in L["refresh"]})
        return {"plan": plan, "total_weeks": total, "debate": debate, "summary": summary}


class Curriculum:
    name = "Curriculum Agent"
    def attach(self, L, plan):
        for it in plan:
            struggled = L["fails"].get(it["skill"], 0) > 0
            pref = ["interactive", "project", "doc", "video"] if struggled else ["video", "doc", "interactive", "project"]
            res = sorted(SK[it["skill"]]["resources"], key=lambda r: pref.index(r[2]) if r[2] in pref else 9)
            it["resources"] = [{"title": r[0], "url": r[1], "type": r[2]} for r in res]
            it["format"] = "hands-on practice (adapted after a struggle)" if struggled else "guided learning + exercises"
        return plan


# ------------------------------------------------------------------ Mentor
class Mentor:
    name = "Mentor Agent"

    def on_fail(self, L, skill):
        L["fails"][skill] = L["fails"].get(skill, 0) + 1
        L["prof"][skill] = 0.3
        pre = sorted(SK[skill]["prereqs"], key=lambda p: L["prof"].get(p, 0))
        if pre and L["prof"].get(pre[0], 0) < 0.8:
            p = pre[0]
            L["prof"][p] = min(L["prof"].get(p, 0), 0.45)
            if p not in L["refresh"]: L["refresh"].append(p)
            return f"You missed {nm(skill)} ({L['fails'][skill]}x). Likely root cause: {nm(p)}. I inserted a refresher on it before you retry."
        return f"You missed {nm(skill)} ({L['fails'][skill]}x). Switching it to hands-on practice at a slower pace."

    def chat(self, L, msg):
        ctx = json.dumps({"goal": ROLES[L["goal"]]["name"], "match": (L.get("gap") or {}).get("match"),
                          "gaps": [nm(s) for s in (L.get("gap") or {}).get("gaps", [])][:6], "hours": L["hours"],
                          "certifications": [e["text"] for e in L.get("certs", [])], "projects": [e["text"] for e in L.get("projects", [])]})
        fb = "Focus on your first roadmap step this week and take its quiz once you finish the exercises. Ask me about any gap skill for a plan."
        return llm.complete_text("You are a warm, concise career mentor. Use the learner context. Give practical next steps, max 5 sentences.", f"Context: {ctx}\nLearner: {msg}", fb)


# --------------------------------------------------------------- Interview
class Interviewer:
    name = "Interviewer Agent"
    def question(self, L, round_="technical", skill=None):
        if round_ == "hr":
            return {"round": "hr", "skill": None, "q": random.choice(HR_QS)}
        if round_ == "project":
            src = next(({"skill": e["skill"], "text": e["text"]} for e in reversed(L.get("evidence", []))), None) or                   next(({"skill": e["skills"][0], "text": e["text"]} for e in reversed(L.get("projects", [])) if e["skills"]), None)
            if src:
                sk = src["skill"]
                fb = f"You wrote: \"{src['text'][:120]}\". Walk me through one design decision you made with {SK[sk]['name']} and what you would change now."
                q = llm.complete_text("You are a technical interviewer. Ask ONE specific follow-up question (max 2 sentences) that probes the candidate's own project, e.g. a design trade-off or a failure they hit. Do not praise.",
                                      json.dumps({"skill": SK[sk]["name"], "project": src["text"]}), fb)
                return {"round": "project", "skill": sk, "q": (q or fb).strip(), "project": src["text"][:160]}
        req = ROLES[L["goal"]]["skills"]
        recent = [i["skill"] for i in L["interviews"][-3:]]
        cand = sorted((s for s in req if s not in recent), key=lambda s: L["prof"].get(s, 0)) or req
        s = skill or next((x for x in cand if L["prof"].get(x, 0) > 0), cand[0])
        return {"round": "technical", "skill": s, "q": Q[s]["interview"]["q"]}

class Evaluator:
    name = "Evaluator Agent"
    def score(self, L, round_, skill, question, answer):
        kws = Q[skill]["interview"]["keywords"] if skill else HR_KW
        a = (answer or "").lower()
        hits = [k for k in kws if k in a]
        miss = [k for k in kws if k not in a]
        base = min(10, round(10 * len(hits) / max(1.0, len(kws) * 0.7)))
        if len(a.split()) < 8: base = min(base, 3)
        fb = {"score": base, "strengths": ["Covered: " + k for k in hits[:3]], "gaps": ["Missing: " + k for k in miss[:3]],
              "followup": f"Can you go deeper on '{miss[0]}'?" if miss else "Good coverage. Add a real example from your own project."}
        out = llm.complete_json("You grade interview answers. JSON: {\"score\":0-10 int,\"strengths\":[str],\"gaps\":[str],\"followup\":str}. Be fair and strict.",
                                json.dumps({"question": question, "answer": answer, "expected_concepts": kws}), fb)
        try:
            out["score"] = max(0, min(10, int(out["score"])))
            out.setdefault("strengths", []); out.setdefault("gaps", []); out.setdefault("followup", "")
        except Exception:
            out = fb
        return out


class EvidenceAgent:
    name = "Evidence Agent"
    SIGNALS = ["built", "deployed", "implemented", "designed", "tested", "database", "api", "endpoint", "github", "users", "%", "latency", "docker", "auth"]

    def score(self, L, skill, text):
        t = (text or "").lower(); words = len(t.split())
        mentions = any(a in t for a in SK[skill]["aliases"])
        sig = [k for k in self.SIGNALS if k in t]
        nums = sum(1 for w in t.split() if any(c.isdigit() for c in w))
        base = (3 if mentions else 0) + min(4, len(sig)) + min(2, nums) + (1 if words >= 40 else 0)
        if words < 15 or not mentions: base = min(base, 4)
        fb = {"score": min(10, base), "reasons": (["Mentions " + SK[skill]["name"]] if mentions else ["Does not mention " + SK[skill]["name"]]) + ["Concrete signals: " + ", ".join(sig[:4])] if sig else ["No concrete implementation details"]}
        out = llm.complete_json("You verify project evidence for a skill claim. Strict: vague claims score low, concrete implementation detail scores high. JSON: {\"score\":0-10 int,\"reasons\":[str]}.",
                                json.dumps({"skill": SK[skill]["name"], "project_description": text}), fb)
        try:
            out["score"] = max(0, min(10, int(out["score"]))); out.setdefault("reasons", [])
        except Exception:
            out = fb
        return out


class JobMatcher:
    name = "Job Match Agent"

    def match(self, L, text):
        t = (text or "").lower()
        req = [k for k, v in SK.items() if any(a in t for a in v["aliases"])]
        ok = [k for k in req if L["prof"].get(k, 0) >= K]
        weak = [k for k in req if k not in ok and L["prof"].get(k, 0) > 0]
        miss = [k for k in req if k not in ok and k not in weak]
        pct = round(100 * len(ok) / len(req)) if req else 0
        fb = (f"You cover {len(ok)} of {len(req)} skills this posting mentions. " + (f"Start with {nm(weak[0] if weak else miss[0])}." if len(ok) < len(req) else "Apply now."))
        advice = llm.complete_text("You are a career coach. In max 3 sentences, say whether to apply to this job given the candidate's verified skills and what to fix first. Be honest.",
                                   json.dumps({"required": [nm(k) for k in req], "verified": [nm(k) for k in ok], "claimed_unverified": [nm(k) for k in weak], "missing": [nm(k) for k in miss]}), fb) if req else "No known skills found in this text."
        return {"match": pct, "required": len(req), "verified": [nm(k) for k in ok], "unverified": [nm(k) for k in weak], "missing": [nm(k) for k in miss],
                "missing_keys": miss + weak, "advice": advice}


class ResumeAgent:
    name = "Resume Agent"

    def bullets(self, L, pp):
        facts = [f"{x['skill']} verified at {int(x['score'] * 100)}% ({', '.join(x['evidence']) or 'evidence on file'})" for x in pp["skills"] if x["verified"]]
        facts += [f"Project: {e['text']}" for e in L.get("evidence", []) if e["ok"]][-3:]
        facts += [f"Listed certification: {c}" for c in pp["certs"]]
        if not facts: return []
        fb = [f"Verified {f}" if "verified" in f else f for f in facts]
        out = llm.complete_json("You write resume bullets. Use ONLY the facts given; never invent numbers, tools, employers or achievements. Certifications are self-listed: write 'Listed certification: X', never 'earned' or 'achieved'. 3 to 6 concise bullets, each starting with a strong verb, plain text. JSON: {\"bullets\":[str]}.",
                                json.dumps({"target_role": pp["goal"], "facts": facts}), {"bullets": fb})
        b = out.get("bullets") if isinstance(out, dict) else None
        return [str(x) for x in b][:6] if isinstance(b, list) and b else fb


# --------------------------------------------------------------- Recruiter
class Recruiter:
    name = "Recruiter Agent"
    HIRE_MATCH = 80

    @staticmethod
    def hr_avg(L):
        return sum(L["hr"]) / len(L["hr"]) if L["hr"] else None

    def decide(self, prof, hr, L):
        g = GapAnalyst().run({**L, "prof": prof})
        hr_ok = hr is not None and hr >= 5
        return g["match"] >= self.HIRE_MATCH and hr_ok, g["match"]

    def rejection(self, L, gap):
        hr = self.hr_avg(L)
        gaps = sorted((t for t in gap["tests"] if t["status"] != "pass"), key=lambda t: t["score"])
        # candidate fixes ranked by how much match they recover; behavioral gate first
        cands = ([{"kind": "hr"}] if hr is None or hr < 5 else []) + [{"kind": "skill", "t": t} for t in gaps]
        prof, hr_sim = dict(L["prof"]), hr
        ok, match_now = self.decide(prof, hr_sim, L)
        steps = []
        for c in cands:
            if ok: break
            if c["kind"] == "hr":
                hr_sim = 6.0
                steps.append({"skill": "Behavioral (STAR)", "fix": "Practise 3 STAR answers and pass the HR round at 5/10 or higher", "weeks": 1})
            else:
                t = c["t"]; prof[t["skill"]] = .85
                steps.append({"skill": t["name"], "fix": f"Verify {t['name']} and ship a small project using it", "weeks": weeks(L, t["skill"])})
            ok, after = self.decide(prof, hr_sim, L)
        after = self.decide(prof, hr_sim, L)[1]
        decision_now = self.decide(L["prof"], hr, L)[0]
        fixes = steps[:3]
        flips = ok and len(steps) <= 3 and not decision_now
        top = gaps[:3]
        reasons = [f"{t['name']}: {t['status']} ({int(t['score'] * 100)}%)" for t in top]
        if hr is None: reasons.append("Behavioral: no HR/STAR round completed")
        elif hr < 5: reasons.append(f"Behavioral: STAR answers average {hr:.1f}/10")
        fb = ("Thank you for applying. We are not moving forward because your profile does not yet show proof of: " + "; ".join(reasons) +
              ". Come back after addressing these and showing verified work.") if not decision_now else "You pass the skills screen. Differentiate with projects and a strong portfolio."
        letter = llm.complete_text("You are a strict but fair recruiter writing a short honest rejection for a candidate. List concrete evidence gaps. No fluff, 5 sentences max.",
                                   json.dumps({"role": ROLES[L["goal"]]["name"], "gaps": reasons}), fb)
        return {"letter": letter, "reasons": reasons, "fixes": fixes, "match_now": gap["match"], "match_after": after,
                "decision_now": "HIRE" if decision_now else "REJECT", "decision_after": "HIRE" if ok else "REJECT",
                "flips": flips, "fixes_needed": len(steps), "hire_bar": self.HIRE_MATCH, "behavioral": hr}


# ------------------------------------------------- Organisation-side agents
class CohortAnalyst:
    name = "Cohort Analyst"
    def report(self, learners):
        n = len(learners); freq = {}
        for L in learners:
            for s in ((L.get("gap") or {}).get("gaps") or []):
                freq[s] = freq.get(s, 0) + 1
        top = sorted(freq.items(), key=lambda x: -x[1])[:6]
        starts = [(L.get("timeline") or [{"match": 0}])[0]["match"] for L in learners]
        nows = [(L.get("gap") or {}).get("match", 0) for L in learners]
        impact = {"before": round(sum(starts) / n) if n else 0, "after": round(sum(nows) / n) if n else 0,
                  "improved": sum(1 for a, b in zip(starts, nows) if b > a)}
        return {"learners": n, "impact": impact, "avg_match": round(sum((L.get("gap") or {}).get("match", 0) for L in learners) / n) if n else 0,
                "top_gaps": [{"skill": nm(s), "count": c, "pct": round(100 * c / n)} for s, c in top],
                "roster": [{"name": L["name"], "goal": ROLES[L["goal"]]["name"], "match": (L.get("gap") or {}).get("match", 0)} for L in sorted(learners, key=lambda x: -(x.get("gap") or {}).get("match", 0))]}

    def syllabus(self, text, role):
        t = text.lower(); req = ROLES[role]["skills"]
        covered = [s for s in req if any(a in t for a in SK[s]["aliases"])]
        missing = [s for s in req if s not in covered]
        pct = round(100 * len(covered) / len(req))
        fb = ("Add modules on: " + ", ".join(nm(s) for s in missing[:4]) + ".") if missing else "Syllabus covers every required skill."
        advice = llm.complete_text("You advise a university on curriculum gaps in 3 sentences.", json.dumps({"role": ROLES[role]["name"], "missing": [nm(s) for s in missing]}), fb)
        return {"role": ROLES[role]["name"], "coverage": pct, "covered": [nm(s) for s in covered], "missing": [nm(s) for s in missing], "advice": advice}
