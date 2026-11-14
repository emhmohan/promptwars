# CareerPipe: Career CI/CD

An open-source, multi-agent career mentor. It treats your career like a codebase: it runs "tests" on your skills,
shows what is failing, lets a council of agents debate the fastest fix, re-plans when you struggle or change goals,
runs a mock interview, writes an honest rejection review, and issues a verified skill passport.
Organisations get a cohort dashboard and a syllabus gap analyzer.

## Quick start (VS Code)
1. Install Python 3.10+ and open this folder in VS Code (File > Open Folder).
2. Open the terminal (Ctrl+`) and run:
   - Windows: `run.bat`
   - Mac/Linux: `./run.sh`
3. Open http://localhost:8000
4. It works immediately with no API key (rule-based agents). To use a real LLM, see CareerPipe_Guide.pdf and edit `.env`.

Manual setup: `python -m venv .venv`, activate it, `pip install -r requirements.txt`, copy `.env.example` to `.env`,
then `uvicorn backend.main:app --reload`.  Tests: `pytest -q tests`.

## Structure
- `backend/agents.py`: Profile, Assessment, Gap Analyst, Council (Strategist, Pedagogy, Time Budget, Arbiter), Curriculum, Mentor, Interviewer, Evaluator, Recruiter, Cohort Analyst
- `backend/orchestrator.py`: event router; every handoff is logged and shown in the UI
- `backend/llm.py`: Gemini / OpenAI / Anthropic / Ollama / mock, with safe fallback on any error
- `backend/data/skills.json`, `questions.json`: open skill graph, roles, resources, question bank (contributions welcome)
- `frontend/`: dependency-free UI served by FastAPI

## Add a role or skill
Edit `backend/data/skills.json` (skill with prereqs, weeks, aliases, resources; role listing skill ids) and add an entry to `questions.json` (`mcq` + two `more` questions + an `interview` prompt). No code change needed.

License: MIT.

## Demo
Click **Load demo cohort** in the Organisation tab (or `POST /api/demo/seed`) to seed six learners with verified progress.
Five-minute walkthrough: see `docs/CareerPipe_Guide.html` / `CareerPipe_Guide.pdf`. For a clean demo set `CAREERPIPE_DB` to a fresh file.

## Also included
- **Certifications and projects** in the profile; skills they mention are added as claims to verify.
- **Career matching**: every role ranked by match, with the top gaps and a one-click branch switch.
- **Progress timeline**: job match over time, one point per re-plan.
- **Project evidence**: paste a project description; the Evidence Agent scores concrete detail (6/10 or more counts as proof, at a lower proficiency cap than a quiz plus interview).

## Limitations and next steps
- Skill verification is evidence-based (quizzes, interview answers, project evidence), not proctored. Scores are estimates, not certification.
- Storage is a JSON file; swap `store.py` for a database in production.
- Next: GitHub repo analysis for evidence, timed questions, and user accounts.

## Docker
```bash
docker build -t careerpipe .
docker run -p 8000:8000 --env-file .env careerpipe
```
The **Guided demo** button on the onboarding screen replays the full story in one click.
- **Project deep-dive interview:** the Interviewer Agent asks about your own submitted project.
- **Cohort impact:** average job match, first build vs now.
- **Explain my score:** per-skill breakdown of the quiz, interview and project evidence behind each proficiency.
- **Refresh-due nudges:** verified skills that go stale (30+ days or below the bar) are flagged with a one-click re-verify.
- **Resume from proof:** the Resume Agent writes resume bullets using only verified skills, accepted project evidence and listed certifications (no invented facts).
- **Hard test from a document:** in the Verify tab, upload a .txt/.md file (or paste text) of a resume, university course description or job description. The Profile Agent finds the skills, and "Hard test" asks scenario/code-reading questions written from the document (a correct hard answer counts double). Needs an AI provider; without one it falls back to the hardest bank question. PDF upload is not supported, so paste the text.
- **Job match:** paste a real job posting; the Job Match Agent shows how much of it your verified skills cover, what is only claimed, what is missing, and an honest apply-or-not note.
