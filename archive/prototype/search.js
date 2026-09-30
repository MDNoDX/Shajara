/* =====================================================================
   SEARCH — find any person to study them.
   Matches every recorded name form, Latin ↔ Cyrillic, with or without
   o‘ / g‘ apostrophes, small typos, and birth/death years.
   ===================================================================== */
const CYR = {"а":"a","б":"b","в":"v","г":"g","ғ":"g","д":"d","е":"e","ё":"yo","ж":"j","з":"z","и":"i","й":"y","к":"k","қ":"q","л":"l","м":"m","н":"n","о":"o","п":"p","р":"r","с":"s","т":"t","у":"u","ў":"o","ф":"f","х":"x","ҳ":"h","ц":"ts","ч":"ch","ш":"sh","щ":"sh","ъ":"","ь":"","ы":"i","э":"e","ю":"yu","я":"ya","і":"i"};
function translit(s){ return [...String(s||"").toLowerCase()].map(c=>CYR[c] ?? c).join(""); }
/* loose key: script- and spelling-tolerant (Qodirov ~ Кадыров ~ Kodirov, Farrukh ~ Farrux) */
function skel(s){ return fold(translit(s)).replace(/kh/g,"x").replace(/q/g,"k").replace(/x/g,"h").replace(/w/g,"v").replace(/[^\p{L}\p{N}]+/gu," ").trim(); }
const toks = (s) => skel(s).split(" ").filter(Boolean);
function lev(a, b, max){
  if(Math.abs(a.length-b.length) > max) return max+1;
  let prev = Array.from({length:b.length+1}, (_,i)=>i);
  for(let i=1;i<=a.length;i++){
    const cur = [i]; let rowMin = i;
    for(let j=1;j<=b.length;j++){ cur[j] = Math.min(prev[j]+1, cur[j-1]+1, prev[j-1] + (a[i-1]===b[j-1]?0:1)); rowMin = Math.min(rowMin, cur[j]); }
    if(rowMin > max) return max+1; prev = cur;
  }
  return prev[b.length];
}
function tokScore(q, w){
  if(q===w) return 3;
  if(q.length>=2 && w.startsWith(q)) return 2.5;
  if(q.length>=4 && q[0]===w[0]){ const d = lev(q, w, q.length>=7 ? 2 : 1); if(d <= (q.length>=7 ? 2 : 1)) return 1.5; }
  return 0;
}
function personYears(p){
  const ys = new Set();
  ["birth","death"].forEach(tp=>vitalRecords(p.id,tp).forEach(r=>{ const rg = dRange(r.date); if(rg && isFinite(rg[0]) && isFinite(rg[1])) for(let y=rg[0]; y<=rg[1] && y-rg[0]<12; y++) ys.add(String(y)); else if(r.date && r.date.y) ys.add(String(r.date.y)); }));
  return ys;
}
function personPlaces(p){ return [...new Set(eventsOf(p.id).flatMap(e=>[e.placeId, e.toPlaceId]).concat(unionsOf(p.id).map(u=>u.rel.startPlaceId)).filter(Boolean).map(placeName))]; }
/* returns null (no match) or {score, via} */
function searchScore(p, q){
  const qt = toks(q); if(!qt.length) return {score:0, via:null};
  const variants = nameVariants(p).map(v=>({v, t:toks(v)}));
  const years = personYears(p); const ptoks = personPlaces(p).flatMap(toks);
  let total = 0; const hitCount = new Map();
  for(const x of qt){
    let best = 0, bestV = null;
    if(/^\d{4}$/.test(x)){ if(years.has(x)) best = 2; }
    else for(const vv of variants) for(const w of vv.t){ const s = tokScore(x, w); if(s > best){ best = s; bestV = vv.v; } }
    if(!best && x.length>=3 && ptoks.some(w=>tokScore(x,w)>=2.5)) best = 1;
    if(!best) return null;
    total += best; if(bestV) hitCount.set(bestV, (hitCount.get(bestV)||0)+1);
  }
  const via = [...hitCount.entries()].sort((a,b)=>b[1]-a[1])[0];
  return {score: total/qt.length, via: via ? via[0] : null};
}
function matchesName(p, q){ return !String(q||"").trim() || !!searchScore(p, q); }

/* ---------- search state & filters ---------- */
R.S = { q:"", yFrom:"", yTo:"", place:"", sex:"", living:"", branch:"", flag:"" };
function filtersActive(){ const f = R.S; return !!(f.yFrom || f.yTo || f.place || f.sex || f.living || f.branch || f.flag); }
function runSearch(){
  const f = R.S; const q = f.q.trim();
  if(!q && !filtersActive()) return null;
  const y1 = parseInt(f.yFrom,10), y2 = parseInt(f.yTo,10);
  const bm = f.branch ? branchMembers(f.branch) : null;
  const out = [];
  for(const p of Object.values(S.people)){
    const m = q ? searchScore(p, q) : {score:0, via:null}; if(!m) continue;
    if(f.sex && p.sex!==f.sex) continue;
    if(f.living && p.living!==f.living) continue;
    if(bm && !bm.has(p.id)) continue;
    if(Number.isFinite(y1) || Number.isFinite(y2)){
      const rs = vitalRecords(p.id,"birth").map(r=>dRange(r.date)).filter(Boolean);
      const lo = Number.isFinite(y1)? y1 : -Infinity, hi = Number.isFinite(y2)? y2 : Infinity;
      if(!rs.some(r=>r[0] <= hi && r[1] >= lo)) continue;
    }
    if(f.place){ const pq = skel(f.place); if(!personPlaces(p).some(n=>skel(n).includes(pq))) continue; }
    if(f.flag==="conflict" && !unresolvedConflicts(p.id).length) continue;
    if(f.flag==="noparents" && parentsOf(p.id).length) continue;
    if(f.flag==="nosource" && !eventsOf(p.id).some(e=>!citationsOf(e).length)) continue;
    if(f.flag==="nobirth" && vital(p.id,"birth").records.some(r=>r.date && r.date.mode!=="unknown")) continue;
    out.push({p, ...m});
  }
  return out.sort((a,b)=>b.score-a.score || nameOf(a.p).localeCompare(nameOf(b.p)));
}

/* ---------- view ---------- */
function searchHTML(){
  const f = R.S; const ppl = Object.values(S.people);
  const opt2 = (obj, v) => Object.entries(obj).map(([k,l])=>`<option value="${k}" ${v===k?"selected":""}>${esc(l)}</option>`).join("");
  return `<div class="page"><div class="head"><div><h1>${t("Search")}</h1><p class="lede">${t("Find anyone in the archive to study them — by any spelling of the name, in Latin or Cyrillic, or by year and place.")}</p></div></div>
  ${!ppl.length ? `<div class="empty"><h2>${t("No one here yet")}</h2><p>${t("Add people first, then search among them.")}</p><button class="btn primary" data-act="add-person">${t("Add person")}</button></div>` : `
  <div class="bigsearch"><label class="search big"><span class="sr">${t("Name")}</span><svg viewBox="0 0 24 24" aria-hidden="true">${ICON.search}</svg><input id="sq" type="search" autocomplete="off" placeholder="${t("Type a name, e.g. Karim, Карим or Nurmatov 1928")}" value="${esc(f.q)}"></label></div>
  <details class="filters" ${filtersActive()?"open":""}><summary>${t("More filters")}${filtersActive()?` <span class="pill">${t("on")}</span>`:""}</summary>
    <div class="fgrid">
      <label class="fld"><span>${t("Born from year")}</span><input data-sf="yFrom" inputmode="numeric" placeholder="1900" value="${esc(f.yFrom)}"></label>
      <label class="fld"><span>${t("to year")}</span><input data-sf="yTo" inputmode="numeric" placeholder="1950" value="${esc(f.yTo)}"></label>
      <label class="fld"><span>${t("Place")}</span><input data-sf="place" list="placesList" placeholder="${t("e.g. Namangan")}" value="${esc(f.place)}"></label>
      <label class="fld"><span>${t("Sex")}</span><select data-sf="sex"><option value="">${t("Any")}</option>${opt2({male:t("Male"), female:t("Female")}, f.sex)}</select></label>
      <label class="fld"><span>${t("Living or not")}</span><select data-sf="living"><option value="">${t("Any")}</option>${opt2({living:t("Living"), deceased:t("Deceased"), unknown:t("Not sure")}, f.living)}</select></label>
      ${Object.keys(S.branches).length?`<label class="fld"><span>${t("Branch")}</span><select data-sf="branch"><option value="">${t("Any")}</option>${Object.values(S.branches).map(b=>`<option value="${b.id}" ${f.branch===b.id?"selected":""}>${esc(b.name)}</option>`).join("")}</select></label>`:""}
      <label class="fld"><span>${t("Show only")}</span><select data-sf="flag"><option value="">${t("Everyone")}</option>${opt2({conflict:t("Sources disagree"), noparents:t("Parents unknown"), nobirth:t("Birth date unknown"), nosource:t("Facts without a source")}, f.flag)}</select></label>
    </div>
    <button class="link small" data-sclear>${t("Clear filters")}</button>
  </details>${placesDatalist()}
  <div id="sresults" aria-live="polite">${searchResultsHTML()}</div>`}</div>`;
}
function searchResultsHTML(){
  const res = runSearch();
  if(!res){
    const n = Object.keys(S.people).length;
    return `<div class="stips"><p class="muted">${tn(n, "There is {n} person in this archive.", "There are {n} people in this archive.")}</p>
      <h3>${t("Search tips")}</h3><ul class="small muted">
      <li>${t("Latin and Cyrillic both work: “Karim” also finds “Карим”.")}</li>
      <li>${t("Small mistakes are forgiven: “Nurmatof” still finds “Nurmatov”.")}</li>
      <li>${t("Add a year to narrow it down: “Karim 1928”.")}</li>
      <li>${t("Maiden names, nicknames and old spellings are searched too, if they are recorded.")}</li></ul>
      <button class="btn sm" data-sall>${t("Show everyone")}</button></div>`;
  }
  if(!res.length) return `<div class="empty"><h2>${t("No one found")}</h2><p>${t("Try a shorter part of the name, another spelling, or fewer filters. If the person isn’t in the archive yet, add them.")}</p><button class="btn" data-act="add-person">${t("Add person")}</button></div>`;
  const focus = T.focusId && P(T.focusId) ? T.focusId : null;
  return `<p class="small muted" style="margin:0 0 10px">${tn(res.length, "{n} person found", "{n} people found")}</p><div class="sres">${res.slice(0,200).map(({p, via})=>{
    const yl = yearsLine(p); const b = vital(p.id,"birth"); const bp = b.chosen && b.chosen.placeId ? placeName(b.chosen.placeId) : (b.records.find(r=>r.placeId)? placeName(b.records.find(r=>r.placeId).placeId) : "");
    const pars = parentsOf(p.id).map(x=>nameOf(x.person));
    const kin = focus && focus!==p.id ? kinLabel(focus, p.id) : "";
    const conf = unresolvedConflicts(p.id).length, nos = eventsOf(p.id).filter(e=>!citationsOf(e).length).length;
    return `<article class="scard" data-go-person="${p.id}" tabindex="0" role="link" aria-label="${esc(nameOf(p))}">
      <div class="seal sm" aria-hidden="true">${esc(initials(p))}</div>
      <div class="sbody"><h3 translate="no">${esc(nameOf(p))}</h3>
        ${via && via!==nameOf(p) ? `<div class="small muted">${t("Found as")}: <span translate="no">${esc(via)}</span></div>` : ""}
        <div class="small"><span class="${yl.conflict?"err":""}">${esc(yl.text)}</span>${bp?` · ${t("born in {place}",{place:esc(bp)})}`:""}</div>
        <div class="small muted">${pars.length? t("Parents: {list}",{list:esc(pars.join(", "))}) : t("Parents not recorded")}</div>
        ${kin?`<div class="small kin">${t("{kin} of {name}",{kin:esc(kin), name:esc(nameById(focus))})}</div>`:""}
        <div class="row" style="margin-top:6px">${conf?statusBadge("contradicted"):""}${nos?`<span class="tag">${tn(nos,"{n} fact without a source","{n} facts without a source")}</span>`:""}</div>
      </div>
      <div class="sact"><button class="btn sm primary" data-go-person="${p.id}">${t("Study")}</button><button class="btn sm" data-act="show-in-tree" data-id="${p.id}">${t("In the tree")}</button></div>
    </article>`; }).join("")}</div>${res.length>200?`<p class="small muted">${t("Showing the first 200. Add more detail to narrow the search.")}</p>`:""}`;
}
function refreshSearchResults(){ const box = $("#sresults"); if(box) box.innerHTML = searchResultsHTML(); }
let sqTimer = null;
document.addEventListener("input", e=>{
  if(e.target.id==="sq"){ R.S.q = e.target.value; clearTimeout(sqTimer); sqTimer = setTimeout(refreshSearchResults, 120); }
  const sf = e.target.closest && e.target.closest("[data-sf]"); if(sf && sf.tagName==="INPUT"){ R.S[sf.dataset.sf] = sf.value.trim(); clearTimeout(sqTimer); sqTimer = setTimeout(refreshSearchResults, 200); }
});
document.addEventListener("change", e=>{ const sf = e.target.closest && e.target.closest("select[data-sf]"); if(sf){ R.S[sf.dataset.sf] = sf.value; refreshSearchResults(); } });
document.addEventListener("click", e=>{
  if(e.target.closest("[data-sclear]")){ Object.assign(R.S, {yFrom:"", yTo:"", place:"", sex:"", living:"", branch:"", flag:""}); render(); return; }
  if(e.target.closest("[data-sall]")){ R.peopleQ = ""; R.peopleF = "all"; go("people"); return; }
});
document.addEventListener("keydown", e=>{
  if(e.key==="Enter" && e.target.id==="gq"){ R.S.q = e.target.value; e.target.value = ""; go("search"); setTimeout(()=>{ const i = $("#sq"); if(i){ i.focus(); i.setSelectionRange(i.value.length, i.value.length); } }, 30); }
  if(e.key==="Enter" && e.target.classList && e.target.classList.contains("scard")) go("person", e.target.dataset.goPerson);
  if(e.key==="/" && !e.target.closest("input,textarea,select,[contenteditable]") && !$(".modal") && R.screen==="app"){ e.preventDefault(); if(R.view!=="search") go("search"); setTimeout(()=>{ const i = $("#sq"); if(i) i.focus(); }, 30); }
});

/* ---------- "what to find out" block on the profile ---------- */
function studyHTML(p){
  const pid = p.id; const items = [];
  const b = vital(pid,"birth"), d = vital(pid,"death");
  const add = (text, act) => items.push(`<li><span>${text}</span>${act||""}</li>`);
  const btnEv = (type, label) => `<button class="btn sm" data-act="add-event" data-id="${pid}" data-etype="${type}">${label}</button>`;
  if(unresolvedConflicts(pid).length) add(t("Sources disagree — compare them and choose the more reliable record (see above)."));
  if(!b.records.some(r=>r.date && r.date.mode!=="unknown")) add(t("Birth date is unknown."), btnEv("birth", t("Add")));
  if(!b.records.some(r=>r.placeId)) add(t("Birthplace is unknown."), b.records.length ? "" : btnEv("birth", t("Add")));
  const pars = parentsOf(pid);
  if(!pars.some(x=>x.person.sex==="male")) add(t("Father is not recorded."), `<button class="btn sm" data-act="add-rel" data-id="${pid}" data-rel="father">${t("Add")}</button>`);
  if(!pars.some(x=>x.person.sex==="female")) add(t("Mother is not recorded."), `<button class="btn sm" data-act="add-rel" data-id="${pid}" data-rel="mother">${t("Add")}</button>`);
  if(p.living==="unknown") add(t("It is not known whether this person is living."), `<button class="btn sm" data-act="edit-person" data-id="${pid}">${t("Edit")}</button>`);
  if(p.living==="deceased" && !d.records.length) add(t("No record of death yet."), btnEv("death", t("Add")));
  const nos = eventsOf(pid).filter(e=>!citationsOf(e).length).length; if(nos) add(tn(nos, "{n} fact has no source yet.", "{n} facts have no source yet."));
  const weak = [...pars.map(x=>x.rel), ...unionsOf(pid).map(u=>u.rel)].filter(r=>doubtful(r.status)).length; if(weak) add(tn(weak, "{n} family link still needs checking.", "{n} family links still need checking."));
  return `<section class="section study"><div class="sh"><h2>${t("What to find out")}</h2></div>
    ${items.length ? `<ul class="todo">${items.join("")}</ul>` : `<p class="ok small">${t("The main facts are recorded and sourced.")}</p>`}</section>`;
}
