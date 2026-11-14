const $ = s => document.querySelector(s);
const esc = t => String(t ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const tok = () => { try { return localStorage.getItem("cp_tok") || ""; } catch { return ""; } };
const api = async (p, m = "GET", b) => {
  const h = { "Content-Type": "application/json" }; if (tok()) h.Authorization = "Bearer " + tok();
  const r = await fetch("/api" + p, { method: m, headers: h, body: b ? JSON.stringify(b) : undefined });
  if (!r.ok) { const t = await r.text(); let d = t; try { d = JSON.parse(t).detail || t; } catch { } throw new Error(typeof d === "string" ? d : JSON.stringify(d)); }
  return r.json();
};
let USER = null, AUTHERR = "", AUTHNOTE = "";
let META, ST = null, TAB = "build", QZ = null, DQ = [], IV = null, OUT = {}, CHAT = [], BUSY = false;
const IC = {
  check: '<path d="M20 6 9 17l-5-5"/>', x: '<path d="M18 6 6 18M6 6l12 12"/>',
  help: '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
  branch: '<circle cx="6" cy="5.5" r="2.5"/><circle cx="6" cy="18.5" r="2.5"/><circle cx="18" cy="8.5" r="2.5"/><path d="M6 8v8M18 11c0 4-12 2-12 5"/>',
  flask: '<path d="M9 3h6M10 3v6L4.5 19a1.6 1.6 0 0 0 1.4 2.3h12.2a1.6 1.6 0 0 0 1.4-2.3L14 9V3M7.5 15h9"/>',
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L3 21l1.9-5.4A8 8 0 1 1 21 12z"/>',
  tag: '<path d="M20.6 13.4l-7.2 7.2a2 2 0 0 1-2.8 0L3 13V3h10l7.6 7.6a2 2 0 0 1 0 2.8z"/><circle cx="7.5" cy="7.5" r="1"/>',
  building: '<path d="M3 21h18M5 21V7l7-4 7 4v14M9 9h.01M9 13h.01M9 17h.01M15 9h.01M15 13h.01M15 17h.01"/>',
  bot: '<rect x="4" y="8" width="16" height="12" rx="3"/><path d="M12 8V5M9 13v1.5M15 13v1.5M2 14v2M22 14v2"/><circle cx="12" cy="4" r="1"/>',
  play: '<path d="M7 4l13 8-13 8z"/>', alert: '<path d="M12 3 2 20h20L12 3zM12 10v4M12 17h.01"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>', printer: '<path d="M6 9V3h12v6M6 18H4v-7h16v7h-2M6 14h12v7H6z"/>',
  refresh: '<path d="M21 12a9 9 0 1 1-3-6.7L21 8M21 3v5h-5"/>', shield: '<path d="M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3zM9 12l2 2 4-4"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6M16 4.5a3.5 3.5 0 0 1 0 7M18 14c2.2.6 3.5 2.5 3.5 6"/>',
  circle: '<circle cx="12" cy="12" r="8"/>', dot: '<circle cx="12" cy="12" r="4" fill="currentColor"/>',
  term: '<path d="M4 17l6-6-6-6M12 19h8"/>', send: '<path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z"/>',
  list: '<path d="M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01"/>', plus: '<path d="M12 5v14M5 12h14"/>',
  link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
  git: '<circle cx="12" cy="12" r="3"/><path d="M12 3v6M12 15v6"/>', network: '<circle cx="12" cy="5" r="2"/><circle cx="5" cy="19" r="2"/><circle cx="19" cy="19" r="2"/><path d="M12 7v4M12 11l-6 6M12 11l6 6"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>', gauge: '<path d="M12 14l4-4M3.3 17a9 9 0 1 1 17.4 0"/>', sliders: '<path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h12M20 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="8" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
  history: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 2"/>', file: '<path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6zM14 3v6h6M9 15l2 2 4-4"/>',
};
const ic = (n, c = "") => `<svg class="ico ${c}" viewBox="0 0 24 24" aria-hidden="true">${IC[n]}</svg>`;
const TABS = [["build", "Pipeline", "branch"], ["verify", "Unit tests", "flask"], ["interview", "Integration test", "chat"], ["career", "Review & release", "tag"], ["org", "Organisation", "building"], ["mentor", "AI mentor", "bot"]];
const H2 = (i, t, x = "") => `<h2 ${x}>${ic(i, "sm")}${t}</h2>`;
const hash = s => { let h = 2166136261; for (const c of String(s)) h = Math.imul(h ^ c.charCodeAt(0), 16777619); return (h >>> 0).toString(16).padStart(8, "0").slice(0, 7); };
const hue = s => parseInt(hash(s).slice(0, 3), 16) % 360;

async function init() {
  META = await api("/meta"); const s = await api("/status");
  $("#badge").innerHTML = `<span class="dotlive"></span>` + esc(s.provider === "mock" ? "rule-based agents" : `${s.provider} · ${s.model}` + (s.ready ? "" : " · KEY MISSING"));
  let id = localStorage.getItem("sf_id");
  if (tok()) {
    try { const m = await api("/auth/me"); USER = m.username; id = m.learner_id || null; }
    catch { localStorage.removeItem("cp_tok"); id = localStorage.getItem("sf_id"); }
  }
  if (id) { try { ST = await api("/learners/" + id); } catch { localStorage.removeItem("sf_id"); } }
  render();
}
function logout() {
  if (USER) { api("/auth/logout", "POST").catch(() => { }); localStorage.removeItem("cp_tok"); USER = null; }
  AUTHNOTE = ""; localStorage.removeItem("sf_id"); ST = null; OUT = {}; QZ = null; IV = null; CHAT = []; render();
}
function authCard() {
  if (USER) return `<div class="card" style="margin-bottom:12px"><span class="mut">Signed in as <b>${esc(USER)}</b>. ${AUTHNOTE ? esc(AUTHNOTE) : "Your profile is saved to this account."}</span> <button onclick="logout()">Sign out</button></div>`;
  return `<div class="card" style="margin-bottom:12px">${H2("shield", "Sign in to save your progress")}
  <div class="row"><input id="au" type="text" placeholder="username" autocomplete="username" style="max-width:170px"><input id="ap" type="password" placeholder="password (6+ chars)" autocomplete="current-password" style="max-width:190px" onkeydown="if(event.key==='Enter')authGo('login')">
  <button class="p" onclick="authGo('login')">Log in</button><button onclick="authGo('signup')">Create account</button></div>
  ${AUTHERR ? `<p class="mut" style="color:var(--bad)">${esc(AUTHERR)}</p>` : ""}<p class="mut">Optional. Without an account you can still try everything as a guest on this browser.</p></div>`;
}
function authGo(mode) {
  const u = $("#au").value, p = $("#ap").value; AUTHERR = "";
  act(async () => {
    try {
      const r = await api("/auth/" + mode, "POST", { username: u, password: p });
      localStorage.setItem("cp_tok", r.token); USER = r.username; AUTHNOTE = "";
      if (r.learner_id) {
        try { ST = await api("/learners/" + r.learner_id); localStorage.setItem("sf_id", r.learner_id); TAB = "build"; }
        catch { AUTHNOTE = "Logged in, but the saved profile could not be found (it may have been reset). Create your profile below."; }
      } else AUTHNOTE = mode === "login" ? "Logged in. This account has no saved profile yet: create one below and it will be saved here." : "Account created. Create your profile below and it will be saved here.";
    } catch (e) { AUTHERR = e.message + (mode === "login" && /Wrong username/.test(e.message) ? ". If the site was recently redeployed, accounts are reset on free hosting: use Create account again." : ""); }
  });
}
async function act(fn) { if (BUSY) return; BUSY = true; document.body.style.cursor = "progress"; try { await fn(); } catch (e) {
    if (/learner not found|Sign in to the account/.test(e.message)) {
      try { localStorage.removeItem("cp_tok"); localStorage.removeItem("sf_id"); } catch { }
      USER = null; ST = null; OUT = {}; QZ = null; IV = null; CHAT = [];
      AUTHERR = "The server was restarted and its saved data was reset (free hosting has a temporary disk). Please create your profile again.";
    } else alert("Error: " + e.message);
  } BUSY = false; document.body.style.cursor = ""; render(); }

const LBL = { nm: "Your name", gl: "Target role", hr: "Hours per week", rs: "Resume text", ce: "Certifications, one per line", pj: "Projects, one per line", pce: "Certifications, one per line",
  ppj: "Projects, one per line", au: "Username", ap: "Password", dk: "Document type", dt: "Document text", evs: "Skill for project evidence", evt: "Describe your project evidence",
  exs: "Skill to explain", rd: "Interview round", ia: "Your answer", jd: "Job description text", mi: "Message to your mentor", sr: "Syllabus text", st: "Syllabus target role" };
function a11y() {
  document.querySelectorAll("#app input,#app textarea,#app select").forEach(e => {
    if (e.getAttribute("aria-label") || e.closest("label")) return;
    e.setAttribute("aria-label", LBL[e.id] || e.placeholder || e.name || "Field");
  });
  document.querySelectorAll("#app svg:not(.ico)").forEach(s => { s.setAttribute("role", "img"); if (!s.getAttribute("aria-label")) s.setAttribute("aria-label", s.querySelector("title")?.textContent || "Chart"); });
  const live = $("#live"); if (live && ST) live.textContent = `${ST.name}: ${ST.gap.passing} of ${ST.gap.total} role tests passing, ${ST.gap.match} percent match.`;
}
function render() {
  const failing = ST ? ST.gap.total - ST.gap.passing : 0;
  $("#top").innerHTML = ST
    ? `<span class="pill">${ic("branch", "sm")}<b>${esc(ST.goal)}</b></span><span class="pill mono">build #${hash(ST.id + ST.log.length)}</span>
       <span class="pill ${failing ? "bad" : "ok"}">${ic(failing ? "x" : "check", "sm")}${failing ? failing + " failing" : "passing"}</span><span class="sp"></span>
       <span class="mut">${esc(ST.name)} → ${esc(ST.role_name)}</span>${USER ? `<span class="pill">${ic("shield", "sm")}${esc(USER)}</span>` : ""}<button onclick="logout()">${ic("refresh", "sm")}${USER ? "Sign out" : "Switch learner"}</button>`
    : `<span class="kicker">career-ci · open source · self-hosted</span>`;
  $("#tabs").classList.toggle("hide", !ST);
  if (!ST) { $("#app").innerHTML = onboardView(); return a11y(); }
  $("#tabs").innerHTML = TABS.map(([k, n, i]) => `<button class="${TAB === k ? "on" : ""}" ${TAB === k ? 'aria-current="page"' : ""} onclick="TAB='${k}';render()">${ic(i)}${n}</button>`).join("");
  $("#app").innerHTML = { build: buildView, verify: verifyView, interview: interviewView, career: careerView, org: orgView, mentor: mentorView }[TAB]();
  const l = $("#log"); if (l) l.scrollTop = l.scrollHeight;
  a11y();
}

/* ---------- onboarding ---------- */
let CL = new Set(["python", "sql", "html"]), FORM = { nm: "Asha", hr: 8, rs: "", gl: "fs", ce: "", pj: "" };
const lines = t => (t || "").split("\n").map(x => x.trim()).filter(Boolean);
function grab() { if ($("#nm")) FORM = { nm: $("#nm").value, hr: $("#hr").value, rs: $("#rs").value, gl: $("#gl").value, ce: $("#ce").value, pj: $("#pj").value }; }
function tog(k) { grab(); CL.has(k) ? CL.delete(k) : CL.add(k); render(); }
function onboardView() {
  return `<div class="land"><div>
  <div class="kicker">your career, under test</div>
  <h1 style="font-size:42px">Treat your career like a <span class="hl">codebase</span>.</h1>
  <p class="mut" style="font-size:15px">Target role = test suite. Skill gaps = failing tests. A council of agents debates the fastest fix, re-plans when you struggle, and ships you a verified release tag.</p>
  <div class="map"><div><b>role</b>test suite</div><div><b>gaps</b>failing tests</div><div><b>roadmap</b>fix list</div><div><b>interview</b>integration test</div><div><b>goal switch</b>git branch</div><div><b>passport</b>release tag</div></div>
  <div class="term"><div class="bar2"><i></i><i></i><i></i></div><pre><span class="d">$</span> careerpipe test --role fullstack
<span class="g">${ic("check")}</span> Python        pass
<span class="g">${ic("check")}</span> SQL           pass
<span class="y">${ic("help")}</span> HTML          unverified
<span class="r">${ic("x")}</span> JavaScript    missing
<span class="r">${ic("x")}</span> React         missing  <span class="d">(needs JavaScript)</span>
<span class="r">${ic("x")}</span> Node.js       missing
<span class="d">3 failing · council convened · roadmap ~9 weeks</span></pre></div></div>
  <div>${authCard()}<div class="card">${H2("sliders", "Initialise profile")}
  <div class="row"><input id="nm" type="text" placeholder="Your name" value="${esc(FORM.nm)}" style="max-width:200px">
  <select id="gl">${Object.entries(META.roles).map(([k, r]) => `<option value="${k}" ${k === FORM.gl ? "selected" : ""}>${r.name}</option>`).join("")}</select>
  <label class="mut">h/week <input id="hr" type="number" min="1" max="40" value="${FORM.hr}" style="width:64px"></label></div>
  <p class="mut">Skills you claim (we verify them, we don't trust them):</p>
  <div>${Object.entries(META.skills).map(([k, s]) => `<button class="chip ${CL.has(k) ? "on" : ""}" onclick="tog('${k}')">${s.name}</button>`).join("")}</div>
  <p class="mut">Optional resume text, the Profile Agent will pick up skills from it:</p>
  <textarea id="rs" placeholder="e.g. Built a Flask API with PostgreSQL, used Git and Docker...">${esc(FORM.rs)}</textarea>
  <div class="grid g2"><div><p class="mut">Certifications (one per line):</p>
  <textarea id="ce" placeholder="e.g. Google Data Analytics Certificate&#10;freeCodeCamp Responsive Web Design">${esc(FORM.ce)}</textarea></div>
  <div><p class="mut">Projects (one per line):</p>
  <textarea id="pj" placeholder="e.g. Built a Flask REST API with PostgreSQL&#10;Portfolio site in HTML and CSS">${esc(FORM.pj)}</textarea></div></div>
  <div class="row" style="margin-top:12px"><button class="p" onclick="createLearner()">${ic("play", "sm")}Run first build</button><button onclick="guidedDemo()">${ic("play", "sm")}Guided demo (Asha story)</button></div></div></div></div>`;
}
function submitEvidence() {
  const t = $("#evt").value.trim(); if (t.length < 10) return;
  act(async () => { const r = await api(`/learners/${ST.id}/evidence`, "POST", { skill: $("#evs").value, text: t }); ST = r.state; EVR = r.result; });
}
let EVR = null, EXP = null;
const explain = () => act(async () => EXP = await api(`/learners/${ST.id}/explain?skill=${$("#exs").value}`));
function saveProfile() {
  act(async () => { ST = await api(`/learners/${ST.id}/profile`, "PUT", { certifications: lines($("#pce").value), projects: lines($("#ppj").value) }); });
}
function guidedDemo() {
  act(async () => { ST = await api("/demo/guided", "POST"); localStorage.setItem("sf_id", ST.id); TAB = "build"; });
}
function createLearner() {
  grab();
  act(async () => {
    ST = await api("/learners", "POST", { name: FORM.nm || "Learner", goal: FORM.gl, hours: +FORM.hr || 8, claimed: [...CL], resume_text: FORM.rs, certifications: lines(FORM.ce), projects: lines(FORM.pj) });
    localStorage.setItem("sf_id", ST.id); TAB = "build";
  });
}

/* ---------- pipeline / build status ---------- */
function ring(p) {
  const c = 2 * Math.PI * 62, col = "var(--ink)";
  return `<svg viewBox="0 0 150 150" aria-label="Job match ${p} percent"><circle cx="75" cy="75" r="62" fill="none" stroke="var(--bd)" stroke-width="10"/><circle cx="75" cy="75" r="62" fill="none" stroke="${col}" stroke-width="10" stroke-linecap="round" stroke-dasharray="${c * p / 100} ${c}"/></svg><div class="v"><b>${p}%</b><span>job match</span></div>`;
}
function pipeline() {
  const st = [["profile", 1], ["gap scan", 1], ["council", 1], ["verify", ST.ver.length > 0], ["integration", ST.interviews.length > 0 || ST.hr.length > 0], ["release", ST.ver.some(s => ST.prof[s] >= 0.6)]];
  const run = st.findIndex(x => !x[1]);
  return `<div class="pipe">${st.map(([n, d], i) => `<span class="stage ${d ? "done" : i === run ? "run" : ""}">${ic(d ? "check" : i === run ? "dot" : "circle", "sm")}${n}</span>`).join(`<span class="arrow">${ic("arrow")}</span>`)}</div>`;
}
function depth(s) { const p = META.skills[s].prereqs; return p.length ? 1 + Math.max(...p.map(depth)) : 0; }
function graph() {
  const L = {}; Object.keys(META.skills).forEach(s => (L[depth(s)] = L[depth(s)] || []).push(s));
  const pos = {}, req = META.roles[ST.goal].skills; let rows = 1;
  const CW = 190, RH = 82, R = 15;
  Object.keys(L).forEach(d => { rows = Math.max(rows, L[d].length); L[d].forEach((s, i) => pos[s] = [70 + d * CW, 34 + i * RH]); });
  let e = "", n = "";
  Object.keys(META.skills).forEach(s => META.skills[s].prereqs.forEach(p => {
    const [x1, y1] = pos[p], [x2, y2] = pos[s], ok = (ST.prof[p] || 0) >= 0.6 && (ST.prof[s] || 0) >= 0.6, a = x1 + R + 6, b = x2 - R - 6, m = (b - a) / 2;
    e += `<path class="edge ${ok ? "eok" : ""}" d="M${a} ${y1} C${a + m} ${y1},${b - m} ${y2},${b} ${y2}"/>`;
  }));
  Object.keys(META.skills).forEach(s => {
    const v = ST.prof[s] || 0, c = v >= 0.6 ? "n-ok" : v > 0 ? "n-wk" : "n-no", [x, y] = pos[s], pct = Math.round(v * 100);
    n += `<g><title>${esc(META.skills[s].name)} · ${pct}%${req.includes(s) ? " · required" : ""}</title>${req.includes(s) ? `<circle class="req" cx="${x}" cy="${y}" r="${R + 7}"/>` : ""}<circle class="${c}" cx="${x}" cy="${y}" r="${R}"/>${v >= 0.6 ? `<text class="tick" x="${x}" y="${y + 4}">✓</text>` : ""}<text class="nm" x="${x}" y="${y + 36}">${esc(META.skills[s].name)}</text><text class="pc" x="${x}" y="${y + 49}">${pct ? pct + "%" : "not started"}</text></g>`;
  });
  return `<div class="ov"><svg viewBox="0 0 ${100 + Math.max(...Object.keys(L)) * CW + 80} ${rows * RH + 20}" aria-label="Skill dependency graph: ${Object.keys(META.skills).filter(k => (ST.prof[k] || 0) >= 0.6).length} verified, ${Object.keys(META.skills).filter(k => (ST.prof[k] || 0) > 0 && (ST.prof[k] || 0) < 0.6).length} unverified, of ${Object.keys(META.skills).length} skills. Required for ${esc(ST.role_name)}: ${req.map(k => esc(META.skills[k].name)).join(', ')}" style="min-width:${(Math.max(...Object.keys(L)) + 1) * 150}px">${e}${n}</svg></div>
  <div class="legend mut"><span style="--c:var(--ok)">verified</span><span style="--c:var(--wk)">weak / unverified</span><span style="--c:var(--no)">not started</span><span style="--c:var(--ac2)">required for ${esc(ST.role_name)}</span></div>`;
}
function timeline() {
  const T = (ST.timeline || []).slice(-30); if (T.length < 2) return '<p class="mut">Take a quiz or change the plan to start the timeline.</p>';
  const W = 520, Hh = 120, x = i => 20 + i * (W - 40) / (T.length - 1), y = m => Hh - 10 - m * (Hh - 24) / 100;
  const pts = T.map((p, i) => `${x(i).toFixed(1)},${y(p.match).toFixed(1)}`).join(" ");
  return `<svg viewBox="0 0 ${W} ${Hh + 14}" aria-label="Job match over time, from ${T[0].match} to ${T[T.length - 1].match} percent across ${T.length} builds" style="width:100%;min-width:0"><line x1="20" y1="${y(0)}" x2="${W - 20}" y2="${y(0)}" stroke="var(--bd)"/><line x1="20" y1="${y(80)}" x2="${W - 20}" y2="${y(80)}" stroke="var(--bd)" stroke-dasharray="4 4"/><text x="${W - 22}" y="${y(80) - 3}" font-size="9" text-anchor="end" fill="var(--mut)">hire bar 80%</text>
  <polyline points="${pts}" fill="none" stroke="var(--ink)" stroke-width="2"/>${T.map((p, i) => `<circle cx="${x(i)}" cy="${y(p.match)}" r="3" fill="var(--ink)"><title>${p.match}% · ${esc(p.why)}</title></circle>`).join("")}</svg>
  <div class="mut">${T[0].match}% → <b>${T[T.length - 1].match}%</b> across ${T.length} builds</div>`;
}
const ICON = { pass: ["check", "pass"], weak: ["alert", "weak"], unverified: ["help", "unverified"], missing: ["x", "missing"] };
function buildView() {
  const g = ST.gap, p = ST.plan, fail = g.total - g.passing, hist = ST.history || [];
  return `<section class="card hero"><div class="ring">${ring(g.match)}</div><div>
    <div class="kicker">build #${hash(ST.id + ST.log.length)} · branch ${esc(ST.goal)}</div>
    <h1>${esc(ST.role_name)} <span class="pill ${fail ? "bad" : "ok"}">${fail ? fail + " failing" : "all passing"}</span></h1>
    <div class="mut">${g.passing}/${g.total} role tests passing · ETA about ${p.total_weeks} weeks at ${ST.hours} h/week</div>${pipeline()}</div></section>
  <div class="grid g2" style="margin-top:16px">
  <div class="card">${H2("list", "Test suite · " + esc(ST.role_name))}${g.tests.map(t => `<div class="t"><span class="ic ${ICON[t.status][1]}">${ic(ICON[t.status][0])}</span><span>${esc(t.name)}</span><div class="mini ${t.status}"><i style="width:${Math.max(4, t.score * 100)}%"></i></div><span class="lab ${t.status}">${t.status} ${Math.round(t.score * 100)}%</span></div>`).join("")}</div>
  <div class="card">${H2("git", "Git checkout · change the plan")}
  <div class="row"><label class="mut">branch (target role) <select onchange="chGoal(this.value)">${Object.entries(META.roles).map(([k, r]) => `<option value="${k}" ${k === ST.goal ? "selected" : ""}>${r.name}</option>`).join("")}</select></label></div>
  <div class="row" style="margin-top:12px"><label class="mut">time budget <input type="range" min="2" max="30" value="${ST.hours}" onchange="chHrs(this.value)"> <b style="color:var(--fg)">${ST.hours} h/week</b></label></div>
  <p class="mut" style="margin-top:14px">${esc(p.summary)}</p>
  <p class="mut">Switching branch or budget re-runs the council instantly. Skills shared between roles stay green.</p>
  ${H2("history", "Assessment history", 'style="margin-top:16px"')}
  ${hist.length ? `<div class="dots">${hist.map(h => `<span class="dot ${h.ok ? "" : "no"}" title="${esc(META.skills[h.skill].name)} · ${h.ok ? "passed" : "failed"}"></span>`).join("")}</div>` : '<p class="mut">No assessments yet. Take a quiz from the roadmap.</p>'}
  ${ST.interviews.length ? `<div class="spark">${ST.interviews.map(i => `<i style="height:${i.score * 10}%" title="${esc(META.skills[i.skill].name)} ${i.score}/10"></i>`).join("")}</div><div class="mut">interview scores</div>` : ""}</div>
  ${(ST.stale || []).length ? `<div class="card span">${H2("alert", "Refresh due · skills going stale")}<p class="mut">Skills fade without practice (120-day half-life). Re-verify these before they drop below the 60% bar.</p>${ST.stale.map(x => `<div class="row" style="justify-content:space-between;margin-bottom:6px"><span><b>${esc(x.name)}</b> · ${Math.round(x.score * 100)}% · verified ${x.days} day(s) ago${x.score < 0.6 ? " · <span class='missing'>below bar</span>" : ""}</span><button onclick="startQuiz('${x.skill}')">${ic("refresh", "sm")}Re-verify</button></div>`).join("")}</div>` : ""}
  <div class="card">${H2("network", "Career matching · best-fit roles")}
  ${(ST.roles || []).map(r => `<div style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;font-weight:600"><span>${esc(r.name)}${r.current ? ' · target' : ""}</span><span>${r.match}%</span></div><div style="height:8px;background:var(--soft);border-radius:4px;margin:4px 0"><div style="height:8px;border-radius:4px;background:var(--ink);width:${Math.max(3, r.match)}%"></div></div>
  <div class="mut">${r.passing}/${r.total} tests pass${r.top_gaps.length ? " · next: " + r.top_gaps.map(esc).join(", ") : ""}${r.current ? "" : ` · <a href="#" onclick="chGoal('${r.role}');return false">switch branch</a>`}</div></div>`).join("")}</div>
  <div class="card">${H2("history", "Progress timeline · job match over time")}${timeline()}</div>
  <div class="card span">${H2("list", "Profile · certifications and projects")}
  <div class="grid g2"><div><p class="mut">Certifications (one per line)</p><textarea id="pce">${esc((ST.certs || []).map(e => e.text).join("\n"))}</textarea></div>
  <div><p class="mut">Projects (one per line)</p><textarea id="ppj">${esc((ST.projects || []).map(e => e.text).join("\n"))}</textarea></div></div>
  <p class="mut">Skills mentioned here are added as claims for the Assessment Agent to verify: ${[...new Set([...(ST.certs || []), ...(ST.projects || [])].flatMap(e => e.skills))].map(k => META.skills[k].name).join(", ") || "none yet"}.</p>
  <div class="row"><button onclick="saveProfile()">${ic("check", "sm")}Save profile</button></div></div>
  <div class="card">${H2("file", "Explain my score · how it was computed")}
  <div class="row"><select id="exs">${Object.entries(META.skills).map(([k, v]) => `<option value="${k}" ${EXP && EXP.key === k ? "selected" : ""}>${esc(v.name)}</option>`).join("")}</select><button onclick="explain()">Explain</button></div>
  ${EXP ? `<p><b>${EXP.skill}: ${Math.round(EXP.score * 100)}%</b> · ${EXP.passes ? "passes" : "below"} the ${Math.round(EXP.threshold * 100)}% bar</p>${EXP.evidence.map(e => `<p class="mut">${esc(e)}</p>`).join("")}<p class="mut">${esc(EXP.rule)}</p>${EXP.days_since_verified !== null ? `<p class="mut">Last verified ${EXP.days_since_verified} day(s) ago (skills decay with a 120-day half-life).</p>` : ""}<p><b>${esc(EXP.next)}</b></p>` : '<p class="mut">Pick a skill to see which quiz, interview and project results produced its score.</p>'}</div>
  <div class="card span">${H2("shield", "Project evidence · prove a skill with your work")}
  <p class="mut">Paste a project or repo description for one skill. The Evidence Agent scores it for concrete detail; 6/10 or more counts as proof.</p>
  <div class="row"><select id="evs">${Object.entries(META.skills).map(([k, v]) => `<option value="${k}">${esc(v.name)}</option>`).join("")}</select></div>
  <textarea id="evt" placeholder="e.g. Built a REST API in Flask with PostgreSQL, deployed on Render, 200 users, JWT auth, tested with pytest"></textarea>
  <div class="row"><button onclick="submitEvidence()">${ic("check", "sm")}Verify evidence</button></div>
  ${EVR ? `<p><b>${EVR.score}/10</b> · ${EVR.score >= 6 ? "accepted" : "not enough"} · ${(EVR.reasons || []).map(esc).join(" · ")}</p>` : ""}</div>
  <div class="card span">${H2("network", "Skill graph · dependency tree")}${graph()}</div>
  <div class="card">${H2("list", "Fix list · adaptive roadmap")}${p.steps.length ? `<div class="tl">${p.steps.map((s, i) => `<div class="step ${s.refresher ? "ref" : ""}"><b>${i + 1}. ${esc(s.name)}</b>${s.refresher ? '<span class="tag2">refresher</span>' : ""} <span class="mut">· ${s.weeks} wk from week ${s.start + 1} · ${Math.round(s.score * 100)}%</span>
  <div class="mut">${esc(s.why)} · ${esc(s.format)}</div>
  <div class="res">${s.resources.map(r => `<a href="${esc(r.url)}" target="_blank" rel="noopener">${ic("link", "sm")}${esc(r.title)} · ${esc(r.type)}</a>`).join("")}</div>
  <div class="row"><button onclick="startQuiz('${s.skill}')">${ic("play", "sm")}Run test</button><button onclick="simFail('${s.skill}')">${ic("alert", "sm")}Simulate fail</button></div></div>`).join("")}</div>` : "<p>No gaps. Ship portfolio projects and run a mock interview.</p>"}</div>
  <div class="card">${H2("term", "Agent council · handoff log")}<div class="log" id="log">${ST.log.map(l => `<div><span class="ts">${new Date(l.t * 1000).toLocaleTimeString([], { hour12: false })}</span><span class="ag" style="color:hsl(${hue(l.agent)} 70% 72%)">[${esc(l.agent)}]</span> ${esc(l.msg)}</div>`).join("")}</div></div></div>`;
}
const chGoal = g => act(async () => ST = await api(`/learners/${ST.id}/goal`, "POST", { goal: g }));
const chHrs = h => act(async () => ST = await api(`/learners/${ST.id}/hours`, "POST", { hours: +h }));
const simFail = s => act(async () => ST = await api(`/learners/${ST.id}/simulate-fail`, "POST", { skill: s }));
function startQuiz(s) { TAB = "verify"; DQ = []; act(async () => QZ = { ...(await api(`/learners/${ST.id}/question?skill=${s}&fresh=${$("#fresh")?.checked || false}`)), ctx: "quiz" }); }

/* ---------- verify ---------- */
function verifyView() {
  const todo = ST.claimed.filter(s => !ST.ver.includes(s));
  let h = `<div class="card">${H2("flask", "Unit tests · verify, don't trust")}<p class="mut">Claims are not trusted. Each claimed skill gets quick checks (a different question each time, recent answers weigh more) that turn "I know it" into a verified score.</p>
  <div class="row"><button class="p" onclick="runDiag()" ${todo.length ? "" : "disabled"}>${ic("play", "sm")}Run diagnostic (${todo.length} unverified)</button>
  <select id="pick">${Object.entries(META.skills).map(([k, s]) => `<option value="${k}">${s.name}</option>`).join("")}</select>
  <button onclick="startQuiz($('#pick').value)">Test this skill</button>
  <label class="mut"><input type="checkbox" id="fresh"> fresh AI-written question (needs API key)</label></div></div>`;
  h += `<div class="card" style="margin-top:16px">${H2("file", "Hard test from a document · resume or course description")}
  <p class="mut">Upload a .txt/.md file or paste a resume, university course description or job description. The Profile Agent finds the skills in it, then the Assessment Agent writes hard scenario questions based on what the document claims.</p>
  <div class="row"><select id="dk"><option value="resume">Resume</option><option value="course description">University course description</option><option value="job description">Job description</option></select><input type="file" accept=".txt,.md,text/plain" onchange="loadDoc(this)"></div>
  <textarea id="dt" placeholder="Paste text here...">${esc(OUT.docText || "")}</textarea>
  <div class="row"><button class="p" onclick="readDoc()">${ic("send", "sm")}Find skills</button></div>
  ${OUT.docSkills ? (OUT.docSkills.length ? `<p class="mut">Found ${OUT.docSkills.length} skill(s). Hard questions count double when answered correctly.</p><div class="row">${OUT.docSkills.map(k => `<button onclick="hardTest(['${k}'])">${esc(META.skills[k].name)}</button>`).join("")}<button class="p" onclick="hardTest(${JSON.stringify(OUT.docSkills)})">${ic("play", "sm")}Hard test all</button></div>` : '<p class="mut">No known skills found in this text.</p>') : ""}</div>`;
  if (QZ) h += `<div class="card" style="margin-top:16px">${H2("flask", esc(META.skills[QZ.skill].name) + " · " + QZ.ctx + (QZ.level === "hard-fallback" ? " (no AI provider: hardest bank question)" : ""))}<h3>${esc(QZ.q)}</h3>
  ${QZ.options.map((o, i) => `<button class="opt ${QZ.done ? (i === QZ.ans ? "o-good" : i === QZ.pick ? "o-bad" : "") : ""}" ${QZ.done ? "disabled" : ""} onclick="pick(${i})"><b>${"ABCDEF"[i]}</b><span>${esc(o)}</span></button>`).join("")}
  ${QZ.done ? `<p class="${QZ.ok ? "pass" : "missing"}">${ic(QZ.ok ? "check" : "x")} ${QZ.ok ? "Correct. Evidence recorded." : "Incorrect. Weighted evidence updated; if it drops below the pass bar the Mentor traces the root cause and re-plans."}</p><button class="p" onclick="nextQ()">${DQ.length ? "Next skill" : "Done"}${ic("arrow", "sm")}</button>` : ""}</div>`;
  return h;
}
function loadDoc(inp) { const f = inp.files[0]; if (!f) return; const r = new FileReader(); r.onload = () => { $("#dt").value = r.result; }; r.readAsText(f); }
function readDoc() {
  const t = $("#dt").value.trim(); if (t.length < 20) return;
  act(async () => { const r = await api(`/learners/${ST.id}/document`, "POST", { text: t, kind: $("#dk").value }); ST = r.state; OUT.docSkills = r.skills; OUT.docText = t; });
}
function hardTest(list) { DQ = [...list]; nextQ(true); }
function runDiag() { DQ = ST.claimed.filter(s => !ST.ver.includes(s)); nextQ(false); }
let HARD = false;
function nextQ(h) { if (h !== undefined) HARD = h === true; QZ = null; const s = DQ.shift(); if (!s) { HARD = false; return render(); } act(async () => QZ = { ...(await api(`/learners/${ST.id}/question?skill=${s}&hard=${HARD}`)), ctx: HARD ? "hard test" : "diagnostic" }); }
function pick(i) { act(async () => { const r = await api(`/learners/${ST.id}/answer`, "POST", { skill: QZ.skill, choice: i, context: QZ.ctx }); ST = r.state; QZ.done = true; QZ.pick = i; QZ.ans = r.result.answer; QZ.ok = r.result.correct; }); }

/* ---------- interview ---------- */
function interviewView() {
  let h = `<div class="card">${H2("chat", "Integration test · mock interview")}<p class="mut">Technical answers feed the skill graph (60% weight vs quizzes). HR/STAR answers set your behavioral score, which gates the hire decision in the review.</p>
  <div class="row"><select id="rd"><option value="technical">Technical round</option><option value="project">Project deep-dive (your own work)</option><option value="hr">HR / behavioral round (STAR)</option></select><button class="p" onclick="nextI()">${ic("send", "sm")}Get question</button></div></div>`;
  if (IV) h += `<div class="card" style="margin-top:16px">${H2("chat", IV.round === "hr" ? "HR round" : (IV.round === "project" ? "Project deep-dive · " : "") + esc(META.skills[IV.skill].name))}${IV.project ? `<p class="mut">Based on your project: ${esc(IV.project)}</p>` : ""}<h3>${esc(IV.q)}</h3>
  <textarea id="ia" placeholder="Answer like you would speak it..." ${IV.ev ? "disabled" : ""}>${esc(IV.a || "")}</textarea>
  ${IV.ev ? `<div class="row" style="margin-top:10px"><span class="pill ${IV.ev.score >= 5 ? "ok" : "bad"}">${IV.ev.score}/10</span></div><p class="pass">${IV.ev.strengths.map(esc).join("<br>")}</p><p class="missing">${IV.ev.gaps.map(esc).join("<br>")}</p><p class="mut">Follow-up: ${esc(IV.ev.followup)}</p>`
      : `<div class="row" style="margin-top:10px"><button class="p" onclick="subI()">${ic("send", "sm")}Submit answer</button></div>`}</div>`;
  if (ST.interviews.length || ST.hr.length) h += `<div class="card" style="margin-top:16px">${H2("file", "Test report")}${ST.interviews.map(i => `<div class="t" style="grid-template-columns:1fr auto"><span>${esc(META.skills[i.skill].name)}</span><span class="${i.score >= 5 ? "pass" : "missing"} lab">${i.score}/10</span></div>`).join("")}${ST.hr.length ? `<div class="t" style="grid-template-columns:1fr auto"><span>HR rounds</span><span class="lab">${ST.hr.join(", ")} /10</span></div>` : ""}</div>`;
  return h;
}
const nextI = () => act(async () => IV = await api(`/learners/${ST.id}/interview/next?round=${$("#rd").value}`, "POST"));
const subI = () => act(async () => { const a = $("#ia").value; const r = await api(`/learners/${ST.id}/interview/answer`, "POST", { round: IV.round, skill: IV.skill, question: IV.q, answer: a }); ST = r.state; IV.a = a; IV.ev = r.eval; });

/* ---------- code review + release tag ---------- */
function careerView() {
  const r = OUT.rej, pp = OUT.pass, ver = ST.ver.filter(s => ST.prof[s] != null);
  const hire = r && r.decision_now === "HIRE";
  return `<div class="grid g2"><div class="card">${H2("shield", "Code review · why I would not hire you")}<p class="mut">A strict recruiter agent applies a real hiring bar (${r ? r.hire_bar : 80}% match and a behavioral score of 5/10 or higher), then re-runs the decision with the fixes applied.</p>
  <button class="p" onclick="getRej()">${ic("play", "sm")}Request review</button>
  ${r ? `<div class="row" style="margin-top:14px"><span class="pill ${hire ? "ok" : "bad"}">${ic(hire ? "check" : "x", "sm")}${hire ? "approved" : "changes requested"}</span>${r.behavioral == null ? '<span class="pill wk">' + ic("alert", "sm") + 'no HR round yet</span>' : `<span class="pill">behavioral ${r.behavioral.toFixed(1)}/10</span>`}</div><blockquote>${esc(r.letter)}</blockquote>
  <div class="verdict"><div class="${hire ? "ok" : "bad"}"><small>Decision now</small><b>${r.decision_now}</b><small>${r.match_now}% match</small></div>${ic("arrow", "lg")}<div class="${r.decision_after === "HIRE" ? "ok" : "bad"}"><small>After ${r.fixes_needed} fix${r.fixes_needed === 1 ? "" : "es"}</small><b>${r.decision_after}</b><small>${r.match_after}% match</small></div></div>
  <div class="diff">${r.reasons.map(x => `<div class="d-"><span>${ic("x", "sm")}</span>${esc(x)}</div>`).join("")}${r.fixes.map(f => `<div class="d-p"><span>${ic("plus", "sm")}</span>${esc(f.fix)}<em>~${f.weeks} wk</em></div>`).join("")}</div>
  <p class="mut" style="margin-top:12px">${hire ? "You clear the bar today." : r.flips ? `These ${r.fixes.length} fixes flip the decision to HIRE (simulated by re-running the screen).` : `It takes ${r.fixes_needed} fixes to reach HIRE; the top 3 are shown.`}</p>` : ""}</div>
  <div class="card">${H2("tag", "Release · verified skill passport")}<p class="mut">Only skills with a passing test or interview appear here.</p>
  <div class="row"><button class="p" onclick="getPass()">${ic("tag", "sm")}Tag release</button><button onclick="window.print()">${ic("printer", "sm")}Print / save PDF</button></div>
  ${pp ? `<div class="tagcard" id="passport"><div class="tagtop"><span class="mark">CP</span><div><div class="kicker">release tag</div><h3 style="margin:0" class="mono">v${pp.skills.filter(s => s.verified).length}.0.0-${hash(ST.id + pp.skills.length)}</h3></div><span class="sp"></span><span class="seal">${ic("shield", "sm")}VERIFIED</span></div>
  <p style="margin:12px 0 4px"><b>${esc(pp.name)}</b> <span class="mut">· target ${esc(pp.goal)} · ${pp.match}% match</span></p>
  ${pp.skills.length ? pp.skills.map(s => `<div class="sk"><b>${esc(s.skill)}</b><span class="${s.verified ? "pass" : "weak"} lab">${ic(s.verified ? "check" : "alert", "sm")} ${Math.round(s.score * 100)}%</span><div class="ev">${s.evidence.map(e => `<span>${esc(e)}</span>`).join("")}</div></div>`).join("") : '<p class="mut">No verified skills yet. Run the diagnostic.</p>'}
  ${(pp.certs || []).length ? `<p class="mut">Certifications: ${pp.certs.map(esc).join("; ")}</p>` : ""}
  ${(pp.projects || []).length ? `<p class="mut">Projects: ${pp.projects.map(esc).join("; ")}</p>` : ""}
  ${pp.behavioral != null ? `<p class="mut">Behavioral (STAR) average: <b>${pp.behavioral}/10</b></p>` : ""}
  ${(pp.not_yet_verified || []).length ? `<p class="mut">Not yet verified: ${pp.not_yet_verified.map(esc).join(", ")}</p>` : ""}
  <p class="mut" style="margin-bottom:0">${esc(pp.note)}</p></div>` : ""}</div>
  <div class="card span">${H2("network", "Job match · paste a real job posting")}
  <textarea id="jd" placeholder="Paste a job description here...">${esc(OUT.jdText || "")}</textarea>
  <div class="row"><button onclick="OUT.jdText = $('#jd').value; matchJD()">${ic("send", "sm")}Match me</button></div>
  ${OUT.jd ? `<p><b class="big">${OUT.jd.match}%</b> <span class="mut">of the ${OUT.jd.required} skills it mentions are verified for you</span></p>
  ${OUT.jd.verified.length ? `<p class="pass">Verified: ${OUT.jd.verified.map(esc).join(", ")}</p>` : ""}${OUT.jd.unverified.length ? `<p class="weak">Claimed, not proven: ${OUT.jd.unverified.map(esc).join(", ")}</p>` : ""}${OUT.jd.missing.length ? `<p class="missing">Missing: ${OUT.jd.missing.map(esc).join(", ")}</p>` : ""}
  <p>${esc(OUT.jd.advice)}</p><div class="row">${OUT.jd.missing_keys.slice(0, 4).map(k => `<button onclick="startQuiz('${k}')">Test ${esc(META.skills[k].name)}</button>`).join("")}</div>` : ""}</div>
  <div class="card span">${H2("file", "Resume from proof · bullets from verified evidence only")}
  <div class="row"><button onclick="getResume()">${ic("file", "sm")}Write resume bullets</button>${OUT.res && OUT.res.bullets.length ? `<button onclick="copyResume()">Copy</button>` : ""}</div>
  ${OUT.res ? (OUT.res.bullets.length ? `<ul>${OUT.res.bullets.map(b => `<li>${esc(b)}</li>`).join("")}</ul><p class="mut">${esc(OUT.res.note)}</p>` : '<p class="mut">Nothing verified yet. Pass a quiz or submit project evidence first.</p>') : ""}</div>
  <div class="card span">${H2("clock", "Skill decay · verified skills fade without practice")}
  ${ver.length ? ver.map(s => { const v = ST.prof[s] || 0; return `<div class="dc"><span>${esc(META.skills[s].name)}</span><div class="mini ${v >= 0.6 ? "" : "weak"}"><i style="width:${Math.max(3, v * 100)}%"></i></div><span class="lab">${Math.round(v * 100)}%</span></div>`; }).join("") : '<p class="mut">Verify a skill first, then watch it decay.</p>'}
  <div class="row" style="margin-top:12px">${[30, 90, 180].map(d => `<button onclick="decay(${d})">+${d} days idle</button>`).join("")}</div></div></div>`;
}
const getRej = () => act(async () => OUT.rej = await api(`/learners/${ST.id}/rejection`));
const matchJD = () => { const t = $("#jd").value.trim(); if (t.length < 10) return; act(async () => OUT.jd = await api(`/learners/${ST.id}/jobmatch`, "POST", { text: t })); };
const getResume = () => act(async () => OUT.res = await api(`/learners/${ST.id}/resume`));
const copyResume = () => { navigator.clipboard.writeText(OUT.res.bullets.map(b => "- " + b).join(String.fromCharCode(10))).catch(() => {}); };
const getPass = () => act(async () => OUT.pass = await api(`/learners/${ST.id}/passport`));
const decay = d => act(async () => { ST = await api(`/learners/${ST.id}/decay`, "POST", { days: d }); OUT = {}; });

/* ---------- organisation ---------- */
function orgView() {
  const c = OUT.cohort, s = OUT.syl;
  return `<div class="grid g2"><div class="card">${H2("users", "Cohort dashboard")}<p class="mut">Aggregate gaps across every learner on this server, so universities and teams know what to teach next.</p>
  <div class="row"><button class="p" onclick="getCohort()">${ic("refresh", "sm")}Refresh</button><button onclick="seed()">${ic("plus", "sm")}Add 6 demo learners</button></div>
  ${c ? `<p style="margin-top:14px"><b class="big">${c.learners}</b> <span class="mut">learners · average match</span> <b>${c.avg_match}%</b></p>${c.impact ? `<p><b class="big">${c.impact.before}% → ${c.impact.after}%</b> <span class="mut">average job match, first build vs now · ${c.impact.improved} of ${c.learners} learners improved</span></p>` : ""}${H2("alert", "Most common gaps")}${c.top_gaps.map(g => `<div class="dc" style="grid-template-columns:120px 1fr 70px"><span>${esc(g.skill)}</span><div class="mini missing"><i style="width:${g.pct}%"></i></div><span class="lab">${g.pct}% (${g.count})</span></div>`).join("") || "<p>No data yet.</p>"}
  ${H2("users", "Ranked roster", 'style="margin-top:16px"')}${c.roster.map((r, i) => `<div class="dc" style="grid-template-columns:24px 1fr 1fr 44px"><span class="mut">${i + 1}</span><span>${esc(r.name)} <span class="mut">${esc(r.goal)}</span></span><div class="mini"><i style="width:${r.match}%"></i></div><span class="lab">${r.match}%</span></div>`).join("")}` : ""}</div>
  <div class="card">${H2("file", "Syllabus gap analyzer")}<p class="mut">Paste a course syllabus. We map its topics to the skills a role needs.</p>
  <select id="sr">${Object.entries(META.roles).map(([k, r]) => `<option value="${k}">${r.name}</option>`).join("")}</select>
  <textarea id="st" style="margin:8px 0" placeholder="Unit 1: Python basics. Unit 2: SQL and databases. Unit 3: Statistics...">${esc(OUT.sylText || "")}</textarea>
  <button class="p" onclick="runSyl()">${ic("gauge", "sm")}Analyze coverage</button>
  ${s ? `<p style="margin-top:12px"><b class="big">${s.coverage}%</b> <span class="mut">of ${esc(s.role)} skills covered</span></p><div class="bar"><i style="width:${s.coverage}%"></i></div><p class="pass">${ic("check", "sm")} ${s.covered.map(esc).join(", ") || "none"}</p><p class="missing">${ic("x", "sm")} ${s.missing.map(esc).join(", ") || "none"}</p><p class="mut">${esc(s.advice)}</p>` : ""}</div></div>`;
}
const getCohort = () => act(async () => OUT.cohort = await api("/cohort"));
const seed = () => act(async () => OUT.cohort = await api("/demo/seed", "POST"));
const runSyl = () => act(async () => { OUT.sylText = $("#st").value; OUT.syl = await api("/syllabus", "POST", { text: OUT.sylText, role: $("#sr").value }); });

/* ---------- mentor ---------- */
function mentorView() {
  return `<div class="card">${H2("bot", "AI mentor")}<div>${CHAT.length ? CHAT.map(m => `<div class="msg ${m.me ? "me" : ""}">${esc(m.t)}</div>`).join("") : '<p class="mut">Ask anything about your roadmap.</p>'}</div>
  <div class="row" style="margin:10px 0">${["What should I do this week?", "Why is React after JavaScript?", "Am I ready to apply?"].map(q => `<button class="chip" onclick="ask(this.textContent)">${q}</button>`).join("")}</div>
  <div class="row"><input id="mi" type="text" placeholder="Ask your mentor..." onkeydown="if(event.key==='Enter')ask()" style="flex:1"><button class="p" onclick="ask()">${ic("send", "sm")}Send</button></div></div>`;
}
function ask(t) { const m = (t || $("#mi").value).trim(); if (!m) return; CHAT.push({ me: 1, t: m }); act(async () => { const r = await api(`/learners/${ST.id}/mentor`, "POST", { message: m }); CHAT.push({ t: r.reply }); ST = await api("/learners/" + ST.id); }); }

init();
