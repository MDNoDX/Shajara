/* =====================================================================
   SHELL · ROUTING · VIEWS
   ===================================================================== */
let WS = "demo";            // "demo" | "mine"
let MINE = null;            // {backend, data} once loaded
let mineLoading = false, mineError = null;
let DEMO_ROOT = null;
const R = { view:"dashboard", id:null, peopleQ:"", peopleF:"all", screen:"app" };

const ICON = {
  dashboard:'<path d="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z"/>',
  tree:'<circle cx="12" cy="4.5" r="2"/><circle cx="5" cy="19.5" r="2"/><circle cx="12" cy="19.5" r="2"/><circle cx="19" cy="19.5" r="2"/><path d="M12 6.5v6M5 17.5v-5h14v5M12 12.5v5"/>',
  people:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.6 3.4-5.5 6.5-5.5s5.7 1.9 6.5 5.5"/><path d="M15.5 4.8a3.3 3.3 0 0 1 0 6.4M18 14.8c1.9.7 3.1 2.4 3.5 5.2"/>',
  sources:'<path d="M5 3h10l4 4v14H5z"/><path d="M15 3v4h4M8 11h8M8 15h8M8 19h5"/>',
  settings:'<circle cx="12" cy="12" r="3"/><path d="M12 2.5v3M12 18.5v3M2.5 12h3M18.5 12h3M5.3 5.3l2.1 2.1M16.6 16.6l2.1 2.1M5.3 18.7l2.1-2.1M16.6 7.4l2.1-2.1"/>',
  search:'<circle cx="11" cy="11" r="7"/><path d="M20 20l-4-4"/>'
};
const NAV = [["dashboard","Dashboard"],["search","Search"],["tree","Family tree"],["people","People"],["sources","Sources"],["settings","Settings & backup"]];

function archiveTitle(){ return (S.meta.archive && S.meta.archive.title) || (WS==="demo" ? t("Demo family") : (ACC.cur ? t("{u}’s family archive",{u:ACC.cur.username}) : t("My family archive"))); }
function statusBadge(st){ const s = STATUS[st] || STATUS.unverified; return `<span class="st st-${st||"unverified"}" title="${esc(s.help)}"><i aria-hidden="true">${s.icon}</i>${s.label}</span>`; }
function unknownHTML(t="Unknown"){ return `<span class="unknown">${t}</span>`; }
function toast(msg){ const el = $("#toast"); el.textContent = msg; el.hidden = false; clearTimeout(toast._t); toast._t = setTimeout(()=>el.hidden=true, 4200); }
function updateSaveState(){
  const el = $("#saveState"); if(!el) return;
  let cls = "", txt = "";
  if(WS==="demo"){ cls="demo"; txt="Demo workspace — edits last until you reload."; }
  else if(mineLoading){ cls="busy"; txt="Opening your archive…"; }
  else if(pending){ cls="busy"; txt="Saving…"; }
  else if(lastError){ cls="err"; txt=t("Last change could not be saved. Download a backup from Settings. ({code})",{code:lastError.code||lastError.message||"error"}); }
  else { txt = t(backend.label); if(backend.kind==="memory") cls="err"; }
  el.className = "savestate " + cls; el.innerHTML = `<span class="dot" aria-hidden="true"></span><span>${esc(txt)}</span>`;
}

/* ---------- routing (hash) ---------- */
function go(view, id){ const h = "#/"+view+(id?"/"+id:""); if(location.hash===h) route(); else location.hash = h; }
function route(){
  const [, v="dashboard", id=null] = location.hash.split("/");
  if(v==="login"){ R.screen = "login"; render(); return; }
  R.view = NAV.some(n=>n[0]===v) || v==="person" ? v : "dashboard"; R.id = id;
  if(R.view==="person" && !P(R.id)) R.view = "people";
  closeRail(); render(); const mm = $("main"); if(mm) mm.scrollTop = 0;
  const h1 = $("main h1"); if(h1 && document.activeElement && document.activeElement.closest && !document.activeElement.closest(".modal")) h1.setAttribute("tabindex","-1");
}

/* ---------- shell ---------- */
function renderShell(){
  $("#app").innerHTML = `
  <aside class="rail" id="rail" aria-label="Main">
    <div class="brand"><svg width="34" height="34" viewBox="0 0 34 34" aria-hidden="true"><circle cx="17" cy="17" r="16" fill="none" stroke="currentColor" stroke-opacity=".35"/><circle cx="17" cy="9" r="3" fill="var(--accent)"/><circle cx="10" cy="24" r="3" fill="none" stroke="var(--ink)" stroke-width="1.5"/><circle cx="24" cy="24" r="3" fill="none" stroke="var(--ink)" stroke-width="1.5"/><path d="M17 12v5M10 21v-4h14v4" fill="none" stroke="var(--ink)" stroke-width="1.5"/></svg>
      <div><b>Family Archive</b></div></div>
    ${accountBlockHTML()}
    <div class="ws" role="group" aria-label="Workspace">
      <button data-ws="demo" aria-pressed="${WS==="demo"}">Demo family</button>
      <button data-ws="mine" aria-pressed="${WS==="mine"}">My archive</button>
    </div>
    <label class="search rail-search"><span class="sr">${t("Quick search")}</span><svg viewBox="0 0 24 24" aria-hidden="true">${ICON.search}</svg><input id="gq" type="search" placeholder="${t("Find a person…")}" autocomplete="off"></label>
    <nav class="main">${NAV.map(([k,l])=>`<button data-nav="${k}" ${R.view===k||(k==="people"&&R.view==="person")?'aria-current="page"':""}><svg viewBox="0 0 24 24" aria-hidden="true">${ICON[k]}</svg>${l}</button>`).join("")}</nav>
    <div class="navlater"><b>Coming in later phases</b>Timeline, stories, places, photos, documents, research workspace, reports and the family book.</div>
    ${langSwitchHTML("rail-lang")}
    <div class="savestate" id="saveState" role="status" aria-live="polite"></div>
  </aside>
  <div class="topbar"><button class="btn sm" data-act="rail" aria-label="Open menu" aria-controls="rail">☰</button><b>${esc(archiveTitle())}</b><span class="grow"></span><button class="btn sm" data-nav="search" aria-label="${t("Search")}"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">${ICON.search}</svg></button></div>
  <main id="main"></main>`;
  updateSaveState();
}
function closeRail(){ const r = $("#rail"); if(r) r.classList.remove("open"); }
function accountBlockHTML(){
  if(ACC.cur) return `<div class="acct"><span class="av" aria-hidden="true">${esc(ACC.cur.username.slice(0,1).toUpperCase())}</span><span class="who" translate="no">${esc(ACC.cur.username)}</span><button class="link small" data-logout>${t("Sign out")}</button></div>`;
  return `<div class="acct guest"><span class="small muted">${t("You are not signed in.")}</span><button class="btn sm primary" data-login="in">${t("Sign in")}</button></div>`;
}
function render(){
  if(!ACC.ready){ $("#app").innerHTML = `<div class="boot"><p class="muted">${t("Opening…")}</p></div>`; return; }
  if(R.screen==="login"){ renderLogin(); return; }
  renderShell();
  const m = $("#main");
  const banner = WS==="demo" ? `<div class="demo-banner" role="note"><strong>DEMO DATA</strong><span>A fictional family for exploring the app. Nothing here is real, and nothing here is saved to your archive.</span><button class="link" data-ws="mine">Go to my archive</button></div>` : "";
  if(WS==="mine" && mineLoading){ m.innerHTML = `<div class="page"><h1>${esc(archiveTitle())}</h1><p class="lede">${t("Opening your archive…")}</p></div>`; return; }
  const v = R.view;
  if(v==="tree"){ m.innerHTML = banner + treePageHTML(); m.style.overflow="hidden"; renderTreeCanvas(!T.hasView); return; }
  m.style.overflow = "";
  m.innerHTML = banner + ({dashboard:dashboardHTML, search:searchHTML, people:peopleHTML, person:()=>profileHTML(R.id), sources:sourcesHTML, settings:settingsHTML}[v] || dashboardHTML)();
  if(v==="dashboard") drawMiniTree();
}

/* ---------- dashboard ---------- */
function gaps(){
  const ppl = Object.values(S.people); const g = [];
  const link = (p) => `<li><button class="link" data-go-person="${p.id}">${esc(nameOf(p))}</button></li>`;
  const add = (items, one, many, fmt=link) => { if(items.length) g.push({n:items.length, text: items.length===1? one : many.replace("{n}",items.length), list: items.map(fmt).join("")}); };
  add(ppl.filter(p=>unresolvedConflicts(p.id).length), "person has conflicting records that need research.", "people have conflicting records that need research.");
  add(ppl.filter(p=>{ const v=vital(p.id,"birth"); return !v.records.length || v.records.every(r=>!r.date||r.date.mode==="unknown"); }), "person has an unknown birth date.", "people have unknown birth dates.");
  add(ppl.filter(p=>!vital(p.id,"birth").records.some(r=>r.placeId)), "person has an unknown birthplace.", "people have unknown birthplaces.");
  add(ppl.filter(p=>!parentsOf(p.id).length), "person has no parents recorded.", "people have no parents recorded.");
  add(ppl.filter(p=>p.living==="deceased" && !vital(p.id,"death").records.length), "deceased person has no death record.", "deceased people have no death record.");
  add(ppl.filter(p=>p.living==="unknown"), "person's living status is unknown.", "people's living status is unknown.");
  const rv = rels().filter(r=>doubtful(r.status));
  add(rv, "relationship requires verification.", "relationships require verification.", r=>`<li><button class="link" data-go-person="${r.childId||r.aId}">${esc(describeRel(r))}</button> ${statusBadge(r.status)}</li>`);
  const ns = events().filter(e=>!citationsOf(e).length);
  add(ns, "event has no source.", "events have no source.", e=>{ const pid=((e.participants||[])[0]||{}).personId; return `<li><button class="link" data-go-person="${pid}">${esc(describeEvent(e))}</button> <span class="faint small">${esc(fmtDate(e.date)||"date unknown")}</span></li>`; });
  add(ppl.filter(p=>p.living==="living" && p.privacy==="public"), "living person is marked public.", "living people are marked public.");
  return g;
}
function dashboardHTML(){
  const ppl = Object.values(S.people);
  if(!ppl.length) return `<div class="page"><div class="head"><div><h1>${esc(archiveTitle())}</h1><p class="lede">${ACC.cur? t("Welcome, {u}! Your archive is empty — let’s start.",{u:esc(ACC.cur.username)}) : t("Your archive is empty.")}</p></div></div>
    <div class="empty start"><h2>${t("Three simple steps")}</h2>
    <ol class="steps"><li><b>${t("Add yourself")}</b><span>${t("or the oldest ancestor you know.")}</span></li><li><b>${t("Add parents, children and partners")}</b><span>${t("from the person’s page, with the “Add relative” button.")}</span></li><li><b>${t("Open the family tree")}</b><span>${t("and see how everyone is connected.")}</span></li></ol>
    <p class="small muted">${t("Don’t know something? Leave it empty — an honest gap is better than a guess.")}</p>
    <div class="row" style="justify-content:center"><button class="btn primary" data-act="add-person">${t("Add the first person")}</button><button class="btn" data-nav="settings">${t("Import a backup")}</button></div></div></div>`;
  const living = ppl.filter(p=>p.living==="living").length, dec = ppl.filter(p=>p.living==="deceased").length;
  const unions = rels().filter(r=>r.type==="union").length, pcs = rels().filter(r=>r.type==="parentChild").length;
  const gi = generationInfo();
  const usedPlaces = new Set(events().flatMap(e=>[e.placeId,e.toPlaceId]).concat(rels().map(r=>r.startPlaceId)).filter(Boolean));
  const ys = events().map(e=>e.date&&e.date.y).filter(Boolean); const span = ys.length ? t("Records span {a}–{b}.",{a:Math.min(...ys), b:Math.max(...ys)}) : "";
  const cell = (n,l) => `<div><b>${n}</b><span>${l}</span></div>`;
  const G = gaps();
  const recent = [...ppl.map(p=>({t:p.created, html:`<button class="link" data-go-person="${p.id}">${esc(nameOf(p))}</button>`, k:"Person"})),
    ...Object.values(S.sources).map(s=>({t:s.created, html:esc(s.title), k:"Source"})),
    ...events().map(e=>({t:e.created, html:`<button class="link" data-go-person="${(e.participants[0]||{}).personId}">${esc(describeEvent(e))}</button>`, k:"Event"}))]
    .sort((a,b)=>String(b.t).localeCompare(String(a.t))).slice(0,7);
  return `<div class="page">
  <div class="head"><div><h1>${esc(archiveTitle())}</h1><p class="lede">${tn(ppl.length, "{n} person across {g} generations.", "{n} people across {g} generations.", {g:gi.count})} ${span}</p></div>
    <div class="row"><button class="btn" data-act="add-person">Add person</button><button class="btn primary" data-nav="tree">Open family tree</button></div></div>
  <div class="dash">
    <div style="display:grid;gap:28px;align-content:start">
      <section class="panel" aria-labelledby="ov"><h2 id="ov">Family overview</h2>
        <div class="ledger">${cell(ppl.length,"People")}${cell(living,"Living")}${cell(dec,"Deceased")}${cell(ppl.length-living-dec,"Status unknown")}${cell(gi.count,"Generations")}${cell(unions,"Marriages & unions")}${cell(pcs,"Parent–child links")}${cell(usedPlaces.size,"Places")}${cell(Object.keys(S.sources).length,"Sources")}${cell(events().length,"Events")}${cell(Object.keys(S.branches).length,"Branches")}${cell(events().filter(e=>e.status==="verified").length,"Verified events")}</div>
      </section>
      <section class="panel" aria-labelledby="tp"><div class="panel-head"><h2 id="tp">Family tree</h2><button class="link small" data-nav="tree">Open full view</button></div>
        <button class="minitree" data-nav="tree" aria-label="Open the family tree" id="miniTree"></button></section>
    </div>
    <div style="display:grid;gap:28px;align-content:start">
      <section class="panel" aria-labelledby="rg"><h2 id="rg">Research gaps</h2>
        ${G.length? `<ul class="gaps">${G.map(x=>`<li><details><summary><span class="n">${x.n}</span><span>${esc(x.text)}</span></summary><ul>${x.list}</ul></details></li>`).join("")}</ul>` : `<p class="ok">No open gaps. Every person has dates, places, parents and sourced events.</p>`}
      </section>
      <section class="panel" aria-labelledby="ra"><h2 id="ra">Recently added</h2><ul class="recent">${recent.map(r=>`<li><span>${r.html}</span><span class="faint small">${r.k}</span></li>`).join("")}</ul></section>
    </div>
  </div></div>`;
}
function drawMiniTree(){
  const box = $("#miniTree"); if(!box) return;
  const saved = {mode:T.mode, collapsed:T.collapsed};
  T.mode = "full"; T.collapsed = new Set();
  const L = computeLayout(); T.mode = saved.mode; T.collapsed = saved.collapsed;
  if(!L || !L.box){ box.innerHTML = ""; return; }
  const b = L.box; box.innerHTML = `<svg viewBox="${b.x0-30} ${b.y0-20} ${b.x1-b.x0+60} ${b.y1-b.y0+40}" preserveAspectRatio="xMidYMid meet" aria-hidden="true" class="${(b.x1-b.x0)>3000?"far":""}">${treeContentSVG(L,true)}</svg>`;
}

/* ---------- people ---------- */
function peopleHTML(){
  const all = Object.values(S.people);
  const f = R.peopleF;
  const list = all.filter(p=>matchesName(p, R.peopleQ)).filter(p=> f==="all" || (f==="living"&&p.living==="living") || (f==="deceased"&&p.living==="deceased") || (f==="research" && (unresolvedConflicts(p.id).length || !parentsOf(p.id).length || !vital(p.id,"birth").records.length)))
    .sort((a,b)=>{ const sa=(primaryNameObj(a)||{}).surname||"", sb=(primaryNameObj(b)||{}).surname||""; return sa.localeCompare(sb) || nameOf(a).localeCompare(nameOf(b)); });
  const segBtn = (k,l) => `<button data-pf="${k}" aria-pressed="${f===k}">${l}</button>`;
  const q = R.peopleQ;
  return `<div class="page"><div class="head"><div><h1>People</h1><p class="lede">Search finds every recorded form of a name — birth, married, nicknames and other scripts.</p></div><button class="btn primary" data-act="add-person">Add person</button></div>
  <div class="toolbar"><label class="search"><span class="sr">Search people</span><svg viewBox="0 0 24 24">${ICON.search}</svg><input id="pq" type="search" placeholder="Search names and spellings" value="${esc(q)}"></label>
    <div class="seg" role="group" aria-label="Filter">${segBtn("all","All")}${segBtn("living","Living")}${segBtn("deceased","Deceased")}${segBtn("research","Needs research")}</div></div>
  ${all.length===0 ? `<div class="empty"><h2>No one here yet</h2><p>Add the first person to begin the archive.</p><button class="btn primary" data-act="add-person">Add person</button></div>` :
   list.length===0 ? `<div class="empty"><h2>No matches</h2><p>${t("No one matches “{q}”. Try another spelling, or use Search for more options.",{q:esc(q)})}</p></div>` :
  `<div class="tbl-wrap"><table class="tbl"><thead><tr><th>Name</th><th>Born</th><th>Died</th><th>Parents</th><th>Research</th></tr></thead><tbody>
  ${list.map(p=>{ const b=vital(p.id,"birth"), d=vital(p.id,"death"); const alts = nameVariants(p).filter(v=>v!==nameOf(p)); const sm = q ? searchScore(p, q) : null; const hit = sm && sm.via && sm.via!==nameOf(p) ? sm.via : null;
    const cellV = (v, living) => v.conflict && !v.chosen ? `<span class="st st-conflict"><i>!</i>${esc(v.records.map(r=>yearLabel(r.date)||"?").join(" / "))}</span>` : v.chosen ? `${esc(fmtDate(v.chosen.date)||"Date unknown")}${v.chosen.placeId?`<div class="alt">${esc(placeName(v.chosen.placeId))}</div>`:""}` : living ? `<span class="faint">—</span>` : unknownHTML();
    const issues = unresolvedConflicts(p.id).length ? statusBadge("contradicted") : "";
    return `<tr data-go-person="${p.id}" tabindex="0"><td><div class="pname">${esc(nameOf(p))}</div>${hit?`<div class="alt">${t("Found as")}: ${esc(hit)}</div>`: alts.length?`<div class="alt">${esc(alts.slice(0,3).join(" · "))}</div>`:""}</td>
      <td>${cellV(b)}</td><td>${cellV(d, p.living==="living")}</td><td>${parentsOf(p.id).length ? t("{n} recorded",{n:parentsOf(p.id).length}) : unknownHTML("None recorded")}</td><td>${issues}</td></tr>`; }).join("")}
  </tbody></table></div>`}</div>`;
}

/* ---------- profile ---------- */
function citeLine(o){
  const c = citationsOf(o);
  if(!c.length) return `<div class="cite faint">No source attached</div>`;
  return `<div class="cite"><span>${t("Source:")}</span> ${c.map(x=>esc(S.sources[x.sourceId].title)+(x.detail?` <span class="faint">(${esc(x.detail)})</span>`:"")).join("; ")}</div>`;
}
function vitalDD(p, type){
  const v = vital(p.id, type);
  if(!v.records.length){ if(type==="death" && p.living==="living") return null; return unknownHTML(type==="burial"? "Not recorded" : "Unknown — not yet researched"); }
  if(v.conflict && !v.chosen) return `<span class="st st-conflict"><i>!</i>Conflicting records</span> <span class="small muted">${t("{list} — see below",{list:v.records.map(r=>esc(fmtDate(r.date)||"?")).join(t(" or "))})}</span>`;
  const r = v.chosen; const place = placeName(r.placeId);
  return `<div>${r.date && r.date.mode!=="unknown" ? esc(fmtDate(r.date)) : unknownHTML("Date unknown")}${r.date&&r.date.text?` <span class="faint small">(“${esc(r.date.text)}”)</span>`:""}</div>
    <div class="small">${place? esc(place) : unknownHTML("Place unknown")}</div>
    <div class="row" style="margin-top:4px">${statusBadge(r.status)} ${v.resolution?`<span class="small muted">Preferred record — conflict resolved</span>`:""}${v.records.length>1 && !v.conflict?`<span class="small muted">${t("{n} consistent records",{n:v.records.length})}</span>`:""}</div>`;
}
function profileHTML(pid){
  const p = P(pid); if(!p) return peopleHTML();
  const yl = yearsLine(p); const alts = (p.names||[]).filter(n=>!n.primary);
  const pars = parentsOf(pid), uns = unionsOf(pid).sort(unionSort), kids = childrenOf(pid), sibs = siblingsOf(pid);
  const personLink = (id, meta, relId, relKind) => `<li><div class="who"><button class="link" data-go-person="${id}">${esc(nameById(id))}</button><div class="meta">${meta}</div></div>${relId?`<button class="btn sm ghost" data-edit-rel="${relId}" aria-label="${t("Edit relationship with {name}",{name:esc(nameById(id))})}">Edit</button>`:""}</li>`;
  const yrs = (id) => esc(yearsLine(P(id)).text);
  // children grouped by other parent
  const groups = new Map(); kids.forEach(k=>{ const other = parentsOf(k.person.id).map(x=>x.person.id).filter(x=>x!==pid); const key = uns.find(u=>other.includes(u.partnerId))?.partnerId || other[0] || ""; if(!groups.has(key)) groups.set(key,[]); groups.get(key).push(k); });
  const conflicts = SINGULAR.map(t=>({t, v:vital(pid,t)})).filter(x=>x.v.conflict);
  const evs = eventsOf(pid).sort((a,b)=>(dSort(a.date)??9e9)-(dSort(b.date)??9e9));
  const brs = branchesOf(pid);
  const usedSources = new Map(); [...evs, ...pars.map(x=>x.rel), ...uns.map(x=>x.rel)].forEach(o=>citationsOf(o).forEach(c=>usedSources.set(c.sourceId,(usedSources.get(c.sourceId)||0)+1)));
  const evStatusCount = {}; evs.forEach(e=>evStatusCount[e.status]=(evStatusCount[e.status]||0)+1);

  return `<div class="page">
  <div class="prof-head">
    <div class="seal" aria-hidden="true">${esc(initials(p))}</div>
    <div><h1 translate="no">${esc(nameOf(p))}</h1><div class="lifespan">${esc(yl.text)}${yl.conflict?` <span class="st st-conflict" style="vertical-align:middle"><i>!</i>dates disagree</span>`:""}</div>
      ${alts.length?`<div class="names-alt"><span>${t("Also recorded as:")}</span> ${alts.map(n=>`${esc(nameText(n)||n.full)} <span class="faint">(${esc(NAME_TYPES[n.type]||n.type)}${n.script&&n.script!=="Latn"&&!["cyrillic","arabic_script"].includes(n.type)?", "+esc(SCRIPTS[n.script]||n.script):""})</span>`).join(" · ")}</div>`:""}
      <div class="row" style="margin-top:10px"><span class="tag">${{living:"Living",deceased:"Deceased",unknown:"Living status unknown"}[p.living]}</span><span class="tag">${t("Privacy: {x}",{x:esc((PRIVACY[p.privacy]||"").split(" — ")[0])})}</span>${brs.map(b=>`<span class="tag">${esc(b.name)}</span>`).join("")}</div></div>
    <div class="prof-actions"><button class="btn" data-act="edit-person" data-id="${pid}">Edit person</button><button class="btn" data-act="add-rel-menu" data-id="${pid}" aria-haspopup="menu">Add relative</button><button class="btn" data-act="show-in-tree" data-id="${pid}">Show in tree</button><button class="btn ghost danger" data-act="delete-person" data-id="${pid}">Delete</button></div>
  </div>

  ${conflicts.map(({t,v})=>conflictHTML(p,t,v)).join("")}

  <div class="prof-grid">
    <div>
      <section class="section"><div class="sh"><h2>Basic information</h2></div>
        <dl class="facts">
          <dt>Full name</dt><dd>${esc(nameOf(p))}</dd>
          <dt>Sex</dt><dd>${p.sex==="unknown"? unknownHTML() : esc(t(p.sex[0].toUpperCase()+p.sex.slice(1)))}</dd>
          <dt>Born</dt><dd>${vitalDD(p,"birth")}</dd>
          ${p.living!=="living"?`<dt>Died</dt><dd>${vitalDD(p,"death")}</dd><dt>Burial</dt><dd>${vitalDD(p,"burial")}</dd>`:""}
        </dl></section>

      <section class="section"><div class="sh"><h2>Family</h2></div>
        <div class="famgroup">Parents</div>
        ${pars.length? `<ul class="fam">${pars.map(x=>personLink(x.person.id, `${esc(parentRole(x.rel.nature, x.person.sex))} · ${yrs(x.person.id)} · ${statusBadge(x.rel.status)}`, x.rel.id)).join("")}</ul>` : `<p class="small">${unknownHTML("No parents recorded.")} <button class="link" data-act="add-rel" data-id="${pid}" data-rel="parent">Add a parent</button></p>`}
        <div class="famgroup">Partners</div>
        ${uns.length? `<ul class="fam">${uns.map(u=>personLink(u.partnerId, `${esc(UNION_TYPE[u.rel.unionType])} · ${u.rel.start&&u.rel.start.mode!=="unknown"?esc(fmtDate(u.rel.start)):t("date unknown")}${u.rel.startPlaceId?", "+esc(placeName(u.rel.startPlaceId)):""}${u.rel.endReason?` · ${t("ended: {x}",{x:esc(UNION_END[u.rel.endReason].toLowerCase())})}${u.rel.endDate&&u.rel.endDate.mode!=="unknown"?" "+esc(fmtDate(u.rel.endDate)):""}`:""} · ${statusBadge(u.rel.status)}`, u.rel.id)).join("")}</ul>` : `<p class="small">${unknownHTML("None recorded.")}</p>`}
        <div class="famgroup">Children</div>
        ${kids.length? [...groups.entries()].map(([other, list])=>`<div class="small muted" style="margin-top:6px">${other? t("With {name}",{name:esc(nameById(other))}) : t("Other parent not recorded")}</div><ul class="fam">${list.sort((a,b)=>byBirth(a.person.id,b.person.id)).map(k=>personLink(k.person.id, `${yrs(k.person.id)}${k.rel.nature!=="biological"?" · "+t("{nature} child",{nature:esc(PC_NATURE[k.rel.nature].toLowerCase())}):""} · ${statusBadge(k.rel.status)}`, k.rel.id)).join("")}</ul>`).join("") : `<p class="small">${unknownHTML("None recorded.")}</p>`}
        <div class="famgroup">Siblings</div>
        ${sibs.length? `<ul class="fam">${sibs.map(s=>personLink(s.id, `${t({full:"Full sibling (both parents shared)", half:"Half-sibling (one parent shared)", unclear:"Sibling — shares one recorded parent; the other parent is not recorded", recorded:"Sibling — recorded directly; parents not linked"}[s.kind])} · ${yrs(s.id)}`, s.rel? s.rel.id : null)).join("")}</ul>` : `<p class="small">${unknownHTML("None recorded.")}</p>`}
      </section>
    </div>
    <div>
      ${studyHTML(p)}
      <section class="section"><div class="sh"><h2>Life events</h2><button class="btn sm" data-act="add-event" data-id="${pid}">Add event</button></div>
        ${evs.length? `<ul class="events">${evs.map(e=>`<li><div class="when">${e.date&&e.date.mode!=="unknown"? esc(fmtDate(e.date)) : unknownHTML("Date unknown")}</div>
          <div class="what">${esc(e.title || EVENT_TYPES[e.type])}${e.title?` <span class="faint small" style="font-family:var(--sans);font-weight:400">${esc(EVENT_TYPES[e.type])}</span>`:""}</div>
          <div class="small">${e.placeId? esc(placeName(e.placeId)) : ""}${e.toPlaceId? " → "+esc(placeName(e.toPlaceId)) : ""}${(e.participants||[]).filter(x=>x.personId!==pid).length? ` · ${t("with {names}",{names:e.participants.filter(x=>x.personId!==pid).map(x=>esc(nameById(x.personId))).join(", ")})}`:""}</div>
          ${e.description?`<div class="small muted" style="margin-top:3px">${esc(e.description)}</div>`:""}
          <div class="row" style="margin-top:5px">${statusBadge(e.status)}<button class="btn sm ghost" data-edit-event="${e.id}">Edit</button></div>${citeLine(e)}</li>`).join("")}</ul>` : `<p class="small">${unknownHTML("No events recorded yet.")}</p>`}
      </section>
      <section class="section"><div class="sh"><h2>Research status</h2></div>
        <dl class="kv"><dt>Events by evidence</dt><dd>${Object.keys(STATUS).filter(k=>evStatusCount[k]).map(k=>`${statusBadge(k)} ${evStatusCount[k]}`).join(" ")||unknownHTML("No events")}</dd>
        <dt>Open conflicts</dt><dd>${unresolvedConflicts(pid).length||"None"}</dd>
        <dt>Sources cited</dt><dd>${usedSources.size? [...usedSources.entries()].map(([id,n])=>`${esc(S.sources[id].title)} <span class="faint">(${n})</span>`).join("<br>") : unknownHTML("None yet")}</dd></dl>
      </section>
      <section class="section"><div class="sh"><h2>Research notes</h2><button class="btn sm" data-act="edit-person" data-id="${pid}">Edit</button></div>
        ${p.notes? `<div class="note" translate="no">${esc(p.notes)}</div>` : `<p class="small">${unknownHTML("No notes yet.")}</p>`}</section>
    </div>
  </div></div>`;
}
function conflictHTML(p, type, v){
  const label = EVENT_TYPES[type].toLowerCase();
  if(v.resolution){
    const r = v.resolution; const chosen = v.records.find(x=>x.id===r.eventId);
    return `<section class="conflict resolved" aria-label="${t("Resolved conflict")}"><h3><span aria-hidden="true">✓</span> ${t("Conflicting {what} records — preferred record chosen",{what:label})}</h3>
      <p class="small" style="margin:8px 0">${t("Preferred:")} <b>${esc(fmtDate(chosen.date)||t("date unknown"))}${chosen.placeId?", "+esc(placeName(chosen.placeId)):""}</b>. ${t("Reason:")} <span translate="no">${esc(r.note)}</span></p>
      <p class="small muted" style="margin:0 0 10px">${t("The other records are kept in the archive and still visible under Life events.")}</p>
      <button class="btn sm" data-act="reopen-conflict" data-id="${p.id}" data-type="${type}">Reopen conflict</button></section>`;
  }
  return `<section class="conflict" aria-label="${t("Conflict detected")}"><h3><span aria-hidden="true">⚠</span> ${t("Sources disagree: {what}",{what:label})}</h3>
    <p class="small" style="margin:6px 0 0">${t("These records say different things. The app does not choose for you — until you decide, both are kept and the {what} is shown as unresolved.",{what:label})}</p>
    <div class="alts">${v.records.map(r=>`<div class="alt-rec"><div><b>${esc(fmtDate(r.date)||"Date unknown")}</b>${r.placeId?`, ${esc(placeName(r.placeId))}`:""}<div class="small muted">${citationsOf(r).map(c=>esc(S.sources[c.sourceId].title)).join("; ")||t("No source")}</div></div><div class="row">${statusBadge(r.status)}<button class="btn sm" data-act="prefer" data-id="${p.id}" data-type="${type}" data-ev="${r.id}">Prefer this record…</button></div></div>`).join("")}</div>
    <p class="small muted" style="margin:0">Status: requires research.</p></section>`;
}

/* ---------- sources ---------- */
function sourcesHTML(){
  const list = Object.values(S.sources).sort((a,b)=>a.title.localeCompare(b.title));
  return `<div class="page narrow"><div class="head"><div><h1>Sources</h1><p class="lede">Documents, interviews and records that support facts in the archive. Attach them to individual events and relationships.</p></div><button class="btn primary" data-act="add-source">Add source</button></div>
  ${!list.length? `<div class="empty"><h2>No sources yet</h2><p>A source is anything that supports a fact: a certificate, an interview with a relative, a letter, an archive record. Facts without a source are listed under research gaps.</p><button class="btn primary" data-act="add-source">Add the first source</button></div>` :
  `<div class="srcs">${list.map(s=>{ const items = allCitingItems(s.id); return `<article class="src"><div class="row" style="justify-content:space-between;align-items:start"><div><h3>${esc(s.title)}</h3><div class="small muted">${esc(SOURCE_TYPES[s.type]||t("Source"))}${s.author?" · "+esc(s.author):""}${s.date&&s.date.mode!=="unknown"?" · "+esc(fmtDate(s.date)):""}${s.reference?" · "+esc(s.reference):""}</div></div><button class="btn sm" data-act="edit-source" data-id="${s.id}">Edit</button></div>
    ${s.reliability?`<p class="small" style="margin:8px 0 0"><b>Reliability:</b> ${esc(s.reliability)}</p>`:""}
    ${s.url?`<p class="small" style="margin:4px 0 0"><a href="${esc(s.url)}" target="_blank" rel="noopener noreferrer">${esc(s.url)}</a></p>`:""}
    <details><summary>${tn(items.length,"Supports {n} claim","Supports {n} claims")}</summary>${items.length?`<ul>${items.map(i=>`<li>${i.kind==="events"? `<button class="link" data-go-person="${(i.obj.participants[0]||{}).personId}">${esc(describeEvent(i.obj))}</button> — ${esc(fmtDate(i.obj.date)||t("date unknown"))}` : `<button class="link" data-go-person="${i.obj.childId||i.obj.aId}">${esc(describeRel(i.obj))}</button>`}</li>`).join("")}</ul>`:`<p class="faint">Not attached to any fact yet.</p>`}</details></article>`; }).join("")}</div>`}</div>`;
}

/* ---------- settings ---------- */
function settingsHTML(){
  const KN = {people:"people", events:"events", rels:"relationships", sources:"sources", places:"places", branches:"branches"};
  const counts = KINDS.filter(k=>k!=="meta").map(k=>t("{n} "+KN[k],{n:Object.keys(S[k]).length})).join(", ");
  return `<div class="page narrow"><div class="head"><div><h1>Settings & backup</h1><p class="lede">Your family history belongs to you. Everything can be downloaded as an open JSON file and restored later.</p></div></div>
  ${accountSettingsHTML()}
  <section class="panel section"><h2>This workspace</h2>
    <dl class="kv" style="margin-top:12px"><dt>Workspace</dt><dd>${WS==="demo"?t("Demo family (fictional, not saved)"):t("My archive")}</dd><dt>Stored</dt><dd>${esc(WS==="demo"? t("In memory only — resets when you reload") : t(backend.label))}</dd><dt>Contents</dt><dd>${esc(counts)}</dd></dl>
    ${WS==="mine"?`<div class="fld" style="margin-top:16px;max-width:420px"><span>Archive title</span><div class="row"><input id="titleIn" value="${esc(archiveTitle())}" style="flex:1"><button class="btn" data-act="save-title">Save title</button></div></div>`:""}
    ${MINE && MINE.data && MINE.data.__truncated ? `<p class="err">Your archive has more than 1,000 records of one kind; only the first 1,000 were loaded. Download a backup before editing.</p>`:""}
  </section>
  <section class="panel section"><h2>Download a backup</h2><p class="hint" style="margin-top:6px">A complete, readable JSON file with every person, name form, relationship, event, citation, source, place and branch.</p>
    <div class="row"><button class="btn primary" data-act="export-json" data-mode="full">Download full backup</button><button class="btn" data-act="export-json" data-mode="share">Download shareable copy</button></div>
    <p class="small muted" style="margin:10px 0 0">The shareable copy keeps living people's names but removes their dates, places and notes, and drops anything marked private.</p><p class="small err" id="dlNote" hidden></p></section>
  <section class="panel section"><h2>Restore from a backup</h2><p class="hint" style="margin-top:6px">Load a JSON backup made by this app into ${WS==="demo"?"the demo workspace (to preview it without saving)":"your archive. It replaces what is there now."}</p>
    <input type="file" id="importFile" accept="application/json,.json" class="sr"><label for="importFile" class="btn">Choose backup file…</label><p class="small" id="importMsg" role="status"></p></section>
  <section class="panel section"><h2>Branches</h2><p class="hint" style="margin-top:6px">A branch is everyone descended from a founder, plus their partners.</p>
    ${Object.values(S.branches).length? `<ul class="fam">${Object.values(S.branches).map(b=>`<li><div class="who"><b>${esc(b.name)}</b><div class="meta">${t("Founder:")} ${P(b.founderId)? esc(nameById(b.founderId)) : `<span class='err'>${t("deleted — choose a new founder")}</span>`} · ${t("{n} people",{n:branchMembers(b.id).size})}</div></div><button class="btn sm" data-act="edit-branch" data-id="${b.id}">Edit</button></li>`).join("")}</ul>` : `<p class="small">${unknownHTML("No branches defined.")}</p>`}
    <button class="btn" data-act="add-branch" style="margin-top:10px">Add branch</button></section>
  ${WS==="mine"?`<section class="panel section"><h2>Delete my archive</h2><p class="hint" style="margin-top:6px">Permanently removes everything in your archive. Download a backup first.</p><button class="btn danger" data-act="wipe">Delete my archive…</button></section>`:`<section class="panel section"><h2>Reset the demo</h2><p class="hint" style="margin-top:6px">Discard your changes to the demo family.</p><button class="btn" data-act="reset-demo">Reset demo data</button></section>`}
  <section class="panel section"><h2>Language</h2><div style="margin-top:10px">${langSwitchHTML()}</div><p class="small muted" style="margin:10px 0 0">Names and notes are always kept exactly as you type them, in any script. Russian is planned for a later phase.</p></section>
  </div>`;
}

function accountSettingsHTML(){
  if(!ACC.cur) return `<section class="panel section"><h2>Account</h2><p class="hint" style="margin-top:6px">${t("Sign in or create an account to keep your own archive.")}</p><div class="row"><button class="btn primary" data-login="in">${t("Sign in")}</button><button class="btn" data-login="new">${t("New account")}</button></div></section>`;
  const a = ACC.cur;
  return `<section class="panel section"><h2>Account</h2>
    <dl class="kv" style="margin-top:12px"><dt>${t("Username")}</dt><dd translate="no">${esc(a.username)}</dd><dt>${t("Created")}</dt><dd>${esc(fmtDate({mode:"exact", y:+a.created.slice(0,4), m:+a.created.slice(5,7), d:+a.created.slice(8,10)}))}</dd><dt>${t("Accounts here")}</dt><dd>${ACC.list.length}</dd></dl>
    <p class="small muted" style="margin:8px 0 12px">${storageNote()} ${t("Each account sees only its own archive.")}</p>
    <div class="row"><button class="btn" data-act="change-pw">${t("Change password")}</button><button class="btn" data-logout>${t("Sign out")}</button><button class="btn ghost danger" data-act="delete-account">${t("Delete account…")}</button></div></section>`;
}

/* ---------- tree page ---------- */
function treePageHTML(){
  const ppl = Object.values(S.people).sort((a,b)=>nameOf(a).localeCompare(nameOf(b)));
  const modes = [["family","Family"],["ancestors","Ancestors"],["descendants","Descendants"],["couple","Couple"],["branch","Branch"],["full","Full tree"]];
  const couples = rels().filter(r=>r.type==="union");
  const needsPerson = ["family","ancestors","descendants"].includes(T.mode);
  return `<div class="tree-page"><div class="tree-bar">
    <div class="seg" role="group" aria-label="Tree view">${modes.map(([k,l])=>`<button data-tmode="${k}" aria-pressed="${T.mode===k}">${l}</button>`).join("")}</div>
    ${needsPerson?`<label class="inl">Person <input list="pplList" id="tFocus" value="${esc(T.focusId&&P(T.focusId)?nameOf(P(T.focusId)):"")}" placeholder="Type a name" aria-label="Focus person"></label>
      <datalist id="pplList">${ppl.map(p=>`<option value="${esc(nameOf(p))}">${esc(yearsLine(p).text)}</option>`).join("")}</datalist>`:""}
    ${T.mode==="couple"?`<label class="inl">Couple <select id="tUnion"><option value="">Choose…</option>${couples.map(u=>`<option value="${u.id}" ${T.unionId===u.id?"selected":""}>${esc(nameById(u.aId))} & ${esc(nameById(u.bId))}</option>`).join("")}</select></label>`:""}
    ${T.mode==="branch"?`<label class="inl">Branch <select id="tBranch"><option value="">Choose…</option>${Object.values(S.branches).map(b=>`<option value="${b.id}" ${T.branchId===b.id?"selected":""}>${esc(b.name)}</option>`).join("")}</select></label><button class="btn sm" data-nav="settings">Branches…</button>`:""}
    ${["family","ancestors"].includes(T.mode)?`<label class="inl">Generations up <select id="tUp">${[1,2,3,4,5,6,8].map(n=>`<option ${T.depthUp===n?"selected":""}>${n}</option>`).join("")}</select></label>`:""}
    ${["family","descendants"].includes(T.mode)?`<label class="inl">Down <select id="tDown">${[1,2,3,4,5,6,8].map(n=>`<option ${T.depthDown===n?"selected":""}>${n}</option>`).join("")}</select></label>`:""}
    <span class="grow"></span>
    ${!T.showLegend?`<button class="btn sm ghost" data-act="legend-on">Line styles</button>`:""}
    <button class="btn sm" data-act="export-tree" data-fmt="svg">Export SVG</button><button class="btn sm" data-act="export-tree" data-fmt="png">Export PNG</button>
  </div><div class="canvas-wrap" id="canvasWrap"></div></div>`;
}
