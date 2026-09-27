/* =====================================================================
   MODALS · FORMS · IMPORT/EXPORT · EVENT WIRING · INIT
   ===================================================================== */
function openModal({title, sub="", body, size="", primary="Save", onPrimary, extra=null, onOpen}){
  const prev = document.activeElement;
  const root = document.createElement("div"); root.className = "scrim";
  root.innerHTML = `<div class="modal ${size}" role="dialog" aria-modal="true" aria-labelledby="mTitle">
    <header><div><h2 id="mTitle">${esc(title)}</h2>${sub?`<p>${sub}</p>`:""}</div><button class="xbtn" data-close aria-label="Close">×</button></header>
    <div class="body">${body}<p class="err" id="mErr" role="alert" hidden></p></div>
    <footer>${extra?`<button class="btn ghost danger" data-extra>${esc(extra.label)}</button>`:"<span></span>"}<div class="row"><button class="btn" data-close>Cancel</button>${primary?`<button class="btn primary" data-primary>${esc(primary)}</button>`:""}</div></footer></div>`;
  document.body.appendChild(root);
  const close = () => { root.remove(); if(prev && prev.focus && document.contains(prev)) prev.focus(); };
  const fail = (msg) => { const e = $("#mErr", root); e.textContent = msg; e.hidden = false; e.scrollIntoView({block:"nearest"}); };
  root.addEventListener("click", async e=>{
    if(e.target===root || e.target.closest("[data-close]")) return close();
    if(e.target.closest("[data-primary]")){ const btn = e.target.closest("[data-primary]"); btn.disabled = true; try{ const err = await onPrimary(root); if(err) fail(err); else close(); } catch(x){ console.error(x); fail("Something went wrong: "+x.message); } finally{ btn.disabled = false; } }
    if(e.target.closest("[data-extra]")){ const err = await extra.fn(root, close); if(err) fail(err); }
  });
  root.addEventListener("keydown", e=>{
    if(e.key==="Escape"){ e.stopPropagation(); close(); }
    if(e.key==="Tab"){ const f = $$('button,input,select,textarea,[tabindex]:not([tabindex="-1"])', root).filter(x=>!x.disabled && x.offsetParent!==null); if(!f.length) return; const a=f[0], z=f[f.length-1]; if(e.shiftKey && document.activeElement===a){ e.preventDefault(); z.focus(); } else if(!e.shiftKey && document.activeElement===z){ e.preventDefault(); a.focus(); } }
  });
  if(onOpen) onOpen(root);
  const first = $("input:not([type=radio]):not([type=checkbox]):not(.sr),select,textarea", $(".body", root)) || $("[data-primary]", root);
  setTimeout(()=>first && first.focus(), 20);
  return {root, close, fail};
}
const opt = (obj, val) => Object.entries(obj).map(([k,l])=>`<option value="${k}" ${String(val)===k?"selected":""}>${esc(l)}</option>`).join("");
const fld = (label, inner, cls="") => `<label class="fld ${cls}"><span>${label}</span>${inner}</label>`;
function statusSelect(name, val="unverified"){ return fld("How certain is this?", `<select name="${name}">${Object.entries(STATUS).map(([k,s])=>`<option value="${k}" ${val===k?"selected":""}>${s.icon} ${s.label} — ${s.help}</option>`).join("")}</select>`); }
function placesDatalist(){ return `<datalist id="placesList">${Object.values(S.places).sort((a,b)=>a.name.localeCompare(b.name)).map(p=>`<option value="${esc(p.name)}">`).join("")}</datalist>`; }
function placeInput(name, id, label="Place"){ return fld(label, `<input name="${name}" list="placesList" value="${esc(placeName(id))}" placeholder="Town or city, as the family knows it" autocomplete="off">`); }

/* fuzzy date widget */
function dateField(p, dt, label){
  dt = dt || {mode:"unknown"}; const mOpts = (v)=>`<option value="">Month</option>`+MON.map((m,i)=>`<option value="${i+1}" ${v===i+1?"selected":""}>${m}</option>`).join("");
  return `<div class="fld"><span>${label}</span><div class="fdate m-${dt.mode}" data-date="${p}">
    <select data-k="mode" aria-label="${esc(t("{label}: how precise",{label:t(label)}))}">${opt(DATE_MODES, dt.mode)}</select>
    <input class="p1 dd" data-k="d" inputmode="numeric" placeholder="Day" aria-label="Day" value="${dt.d||""}">
    <select class="p1 mm" data-k="m" aria-label="Month">${mOpts(dt.m)}</select>
    <input class="p1" data-k="y" inputmode="numeric" placeholder="Year" aria-label="Year" value="${dt.y||""}">
    <div class="two"><span class="and">and</span><input data-k="d2" inputmode="numeric" placeholder="Day" aria-label="End day" value="${dt.d2||""}"><select data-k="m2" aria-label="End month">${mOpts(dt.m2)}</select><input data-k="y2" inputmode="numeric" placeholder="Year" aria-label="End year" value="${dt.y2||""}"></div>
    <input class="txt" data-k="text" placeholder="As written in the source (optional), e.g. “the spring after the flood”" aria-label="Date as written in the source" value="${esc(dt.text||"")}">
  </div></div>`;
}
function readDate(root, p){
  const w = $(`[data-date="${p}"]`, root); if(!w) return {mode:"unknown"};
  const g = (k)=>{ const el = $(`[data-k="${k}"]`, w); return el ? el.value.trim() : ""; };
  const n = (k)=>{ const v = parseInt(g(k),10); return Number.isFinite(v) ? v : null; };
  const mode = g("mode"); const dt = {mode};
  if(mode!=="unknown"){ dt.y = n("y"); if(mode!=="year"){ dt.m = n("m"); if(mode!=="month") dt.d = n("d"); } if(mode==="between"){ dt.y2 = n("y2"); dt.m2 = n("m2"); dt.d2 = n("d2"); } }
  if(g("text")) dt.text = g("text");
  Object.keys(dt).forEach(k=>{ if(dt[k]===null) delete dt[k]; });
  return dt;
}
document.addEventListener("change", e=>{ const s = e.target.closest('[data-date] [data-k="mode"]'); if(s){ const w = s.closest("[data-date]"); w.className = "fdate m-"+s.value; } });

/* citations widget */
function citesField(cites){
  const row = (c={}) => `<div class="cite-row"><select data-c="src" aria-label="Source"><option value="">Choose a source…</option>${Object.values(S.sources).sort((a,b)=>a.title.localeCompare(b.title)).map(s=>`<option value="${s.id}" ${c.sourceId===s.id?"selected":""}>${esc(s.title)}</option>`).join("")}<option value="__new">＋ New source…</option></select><input data-c="detail" placeholder="Page, entry, or time in recording" aria-label="Citation detail" value="${esc(c.detail||"")}"><button type="button" class="btn sm ghost" data-c="rm" aria-label="Remove citation">Remove</button>
    <div class="cite-new" hidden><input data-c="ntitle" placeholder="New source title" aria-label="New source title"><select data-c="ntype" aria-label="New source type">${opt(SOURCE_TYPES,"family_member")}</select></div></div>`;
  return `<div class="fld"><span>Sources for this</span><div class="cites" data-cites>${(cites||[]).map(row).join("")}</div><div><button type="button" class="btn sm" data-c="add" style="margin-top:6px">Attach a source</button></div><template data-cite-tpl>${row()}</template></div>`;
}
document.addEventListener("click", e=>{
  const a = e.target.closest('[data-c="add"]'); if(a){ const f = a.closest(".fld"); const tpl = $("template[data-cite-tpl]", f); $("[data-cites]", f).insertAdjacentHTML("beforeend", tpl.innerHTML); $("[data-cites] .cite-row:last-child select", f).focus(); }
  const r = e.target.closest('[data-c="rm"]'); if(r) r.closest(".cite-row").remove();
});
document.addEventListener("change", e=>{ const s = e.target.closest('[data-c="src"]'); if(s){ const n = $(".cite-new", s.closest(".cite-row")); n.hidden = s.value!=="__new"; if(!n.hidden) $("input", n).focus(); } });
function readCites(root){
  const out = []; let err = null;
  $$("[data-cites] .cite-row", root).forEach(r=>{
    let sid = $('[data-c="src"]', r).value; const detail = $('[data-c="detail"]', r).value.trim();
    if(sid==="__new"){ const nt = $('[data-c="ntitle"]', r).value.trim(); if(!nt){ err = t("Give the new source a title, or remove that citation."); return; } r._new = {title:nt, type:$('[data-c="ntype"]', r).value}; }
    else if(!sid) return;
    out.push({row:r, sourceId:sid, detail});
  });
  if(err) return {err};
  return {commit: () => out.map(c=>{ if(c.sourceId==="__new"){ const s = put("sources", {id:uid("src"), ...c.row._new, date:{mode:"unknown"}}); c.sourceId = s.id; } return {sourceId:c.sourceId, detail:c.detail}; })};
}
const val = (root, name) => { const el = $(`[name="${name}"]`, root); if(!el) return ""; if(el.type==="radio"){ const c = $(`[name="${name}"]:checked`, root); return c? c.value : ""; } return el.value.trim(); };

/* ---------- person ---------- */
function nameRow(n, i){
  n = n || {type:"birth", script:"Latn"};
  return `<div class="namerow" data-name="${n.id||""}"><div class="row" style="justify-content:space-between"><label class="row small"><input type="radio" name="primaryName" value="${i}" ${n.primary||i===0&&!n.id?"checked":""}> Main name shown in the tree</label>${i>0?`<button type="button" class="btn sm ghost" data-rmname>Remove</button>`:""}</div>
    <div class="grid3">${fld("Given name", `<input data-n="given" value="${esc(n.given||"")}">`)}${fld("Patronymic", `<input data-n="patronymic" value="${esc(n.patronymic||"")}" placeholder="e.g. Karimovich, Karim o‘g‘li">`)}${fld("Surname", `<input data-n="surname" value="${esc(n.surname||"")}">`)}</div>
    <details class="more" ${i>0 || (n.type && n.type!=="birth") || (n.script && n.script!=="Latn") || n.full ? "open":""}><summary>${t("Kind of name and script")}</summary><div class="grid3">${fld("Kind of name", `<select data-n="type">${opt(NAME_TYPES, n.type)}</select>`)}${fld("Script", `<select data-n="script">${opt(SCRIPTS, n.script||"Latn")}</select>`)}${fld("Exactly as written (any script)", `<input data-n="full" value="${esc(n.full||"")}" dir="auto">`)}</div></details></div>`;
}
function readNames(root){
  const pi = parseInt(val(root,"primaryName")||"0",10);
  return $$(".namerow", root).map((r,i)=>{ const g = (k)=>$(`[data-n="${k}"]`, r).value.trim(); return {id: r.dataset.name || uid("nm"), type:g("type"), given:g("given"), patronymic:g("patronymic"), surname:g("surname"), full:g("full"), script:g("script"), primary: i===pi}; }).filter(n=>n.given||n.surname||n.full);
}
document.addEventListener("click", e=>{
  if(e.target.closest("[data-addname]")){ const box = $("#nameRows"); box.insertAdjacentHTML("beforeend", nameRow(null, $$(".namerow", box).length)); }
  if(e.target.closest("[data-rmname]")){ const r = e.target.closest(".namerow"); const box = r.parentElement; r.remove(); $$('input[name="primaryName"]', box).forEach((x,i)=>x.value=i); if(!$('input[name="primaryName"]:checked', box)) $('input[name="primaryName"]', box).checked = true; }
});
function openPersonForm(pid){
  const p = pid ? P(pid) : null; const creating = !p;
  const body = `${placesDatalist()}
  <fieldset><legend>Who is this person?</legend><p class="hint">Record every form of the name you know. Nothing you type is changed or transliterated.</p>
    <div id="nameRows">${(p? p.names : [null]).map((n,i)=>nameRow(n,i)).join("")}</div><button type="button" class="btn sm" data-addname>Add another name or spelling</button></fieldset>
  <fieldset><legend>A little more about them</legend><div class="grid2">
    ${fld("Sex", `<select name="sex">${opt({unknown:"Unknown / not recorded", female:"Female", male:"Male", other:"Other"}, p?p.sex:"unknown")}</select>`)}
    ${fld("Are they living?", `<select name="living">${opt({unknown:"Not sure", living:"Living", deceased:"Deceased"}, p?p.living:"unknown")}</select>`)}</div></fieldset>
  ${creating?`<fieldset><legend>When and where were they born?</legend><p class="hint">Leave as “Unknown” if you don’t know — an honest gap is better than a guess.</p>
    ${dateField("birth", null, "Birth date")}<div class="grid2" style="margin-top:10px">${placeInput("birthPlace", null, "Birthplace")}</div>
    <details class="more"><summary>${t("How sure is this, and where is it from?")}</summary><div style="margin-top:8px">${statusSelect("birthStatus")}</div><div style="margin-top:10px">${citesField([])}</div></details></fieldset>
  <fieldset id="deathSet" hidden><legend>When did they die?</legend>${dateField("death", null, "Date of death")}<div class="grid2" style="margin-top:10px">${placeInput("deathPlace", null, "Place of death")}${statusSelect("deathStatus")}</div></fieldset>`:""}
  <details class="more big" ${p && p.notes ? "open" : ""}><summary>${t("Notes and privacy")}</summary>
  <fieldset><legend>What do you know about them?</legend>${fld("Research notes", `<textarea name="notes" placeholder="Who told you what, what you still need to find out, who could confirm it…">${esc(p?p.notes:"")}</textarea>`)}</fieldset>
  <fieldset><legend>Privacy</legend>${fld("Who may see this person", `<select name="privacy">${opt(PRIVACY, p?p.privacy:"private")}</select>`)}<p class="hint" style="margin-top:6px">Living people start as Private. Sharing with family arrives in a later phase; for now this controls what the shareable backup includes.</p></fieldset></details>`;
  openModal({title: creating? t("Add a person") : t("Edit {name}",{name:nameOf(p)}), body, primary: creating? "Add person" : "Save changes",
    onOpen: (root)=>{ const l = $('[name="living"]', root); const upd = ()=>{ const d = $("#deathSet", root); if(d) d.hidden = l.value!=="deceased"; if(creating){ $('[name="privacy"]', root).value = l.value==="deceased"? "family" : "private"; } }; l.addEventListener("change", upd); upd(); },
    onPrimary: (root)=>{
      const names = readNames(root); if(!names.length) return "Enter at least one name — a given name, a surname, or the name as written.";
      if(!names.some(n=>n.primary)) names[0].primary = true;
      const living = val(root,"living"); let privacy = val(root,"privacy");
      if(living==="living" && privacy==="public" && !confirm(t("This person is living and marked Public. Keep it public?"))) return "Choose a different privacy level for this living person.";
      let bd, dd, bc;
      if(creating){ bd = readDate(root,"birth"); const e1 = validateDate(bd); if(e1) return t("Birth date — {e}",{e:e1}); dd = readDate(root,"death"); if(living==="deceased"){ const e2 = validateDate(dd); if(e2) return t("Date of death — {e}",{e:e2}); if(bd.y && dd.y && dd.y < bd.y) return "The date of death is before the birth date."; }
        bc = readCites(root); if(bc.err) return bc.err; }
      const obj = p ? p : {id:uid("p"), resolutions:{}};
      Object.assign(obj, {names, sex:val(root,"sex"), living, privacy, notes:val(root,"notes")});
      put("people", obj);
      if(creating){
        const bp = val(root,"birthPlace");
        if(bd.mode!=="unknown" || bp) put("events", {id:uid("ev"), type:"birth", date:bd, placeId:placeIdFor(bp), participants:[{personId:obj.id, role:"principal"}], status:val(root,"birthStatus"), citations:bc.commit(), description:"", title:""});
        const dp = val(root,"deathPlace");
        if(living==="deceased" && (dd.mode!=="unknown" || dp)) put("events", {id:uid("ev"), type:"death", date:dd, placeId:placeIdFor(dp), participants:[{personId:obj.id, role:"principal"}], status:val(root,"deathStatus"), citations:[], description:"", title:""});
        if(!T.focusId || !P(T.focusId)) T.focusId = obj.id;
        go("person", obj.id); toast(t("Added {name}.",{name:nameOf(obj)}));
      } else { render(); toast("Saved."); }
    }});
}

/* ---------- add a relative ---------- */
const REL_WORD = {father:"father", mother:"mother", parent:"parent", partner:"partner or spouse", child:"child", sibling:"sibling"};
function openAddRelative(pid, relation){
  const p = P(pid); if(!p) return;
  const others = Object.values(S.people).filter(x=>x.id!==pid).sort((a,b)=>nameOf(a).localeCompare(nameOf(b)));
  const sexPreset = relation==="father"?"male":relation==="mother"?"female":"unknown";
  const isParent = ["father","mother","parent"].includes(relation);
  const myParents = parentsOf(pid); const myUnions = unionsOf(pid);
  let relFields = "";
  if(isParent || relation==="child") relFields = `<div class="grid2">${fld("Type of link", `<select name="nature">${opt(PC_NATURE,"biological")}</select>`)}${statusSelect("rstatus","unverified")}</div>`
    + (relation==="child" ? `<div style="margin-top:10px">${fld("Other parent", `<select name="otherParent"><option value="">Not recorded</option>${myUnions.map(u=>`<option value="${u.partnerId}">${esc(nameById(u.partnerId))}</option>`).join("")}</select>`)}</div>` : "");
  if(relation==="partner") relFields = `${placesDatalist()}<div class="grid2">${fld("Kind of union", `<select name="utype">${opt(UNION_TYPE,"marriage")}</select>`)}${statusSelect("rstatus","unverified")}</div>
    <div style="margin-top:10px">${dateField("ustart", null, "Date of marriage or union")}</div><div class="grid2" style="margin-top:10px">${placeInput("uplace", null, "Where")}${fld("Did the union end?", `<select name="uend">${opt(UNION_END,"")}</select>`)}</div>
    <div style="margin-top:10px">${dateField("uendd", null, "When it ended")}</div>`;
  if(relation==="sibling") relFields = myParents.length
    ? `<p class="hint">${t("Siblings are linked through shared parents. Tick the parents they share with {name}.",{name:esc(nameOf(p))})}</p>${myParents.map(x=>`<label class="row small" style="margin:4px 0"><input type="checkbox" name="sharedParent" value="${x.person.id}" checked> ${t("Also a child of {name}",{name:esc(nameOf(x.person))})}</label>`).join("")}<p class="hint">If you untick all, they are recorded as siblings directly.</p><div class="grid2">${fld("If recorded directly", `<select name="sibNature">${opt({unknown:"Sibling — details unknown", full:"Full sibling", half:"Half-sibling", step:"Step-sibling", adoptive:"Adoptive sibling"},"unknown")}</select>`)}${statusSelect("rstatus","unverified")}</div>`
    : `<p class="hint">${t("{name} has no parents recorded, so the sibling link is stored directly. If you add the parents later, link both siblings to them.",{name:esc(nameOf(p))})}</p><div class="grid2">${fld("Kind of sibling", `<select name="sibNature">${opt({unknown:"Sibling — details unknown", full:"Full sibling", half:"Half-sibling", step:"Step-sibling", adoptive:"Adoptive sibling"},"unknown")}</select>`)}${statusSelect("rstatus","unverified")}</div>`;
  const body = `${placesDatalist()}
  <fieldset><legend>Who is it?</legend><div class="choice" role="radiogroup"><label><input type="radio" name="who" value="new" checked> Someone new</label><label><input type="radio" name="who" value="existing" ${others.length?"":"disabled"}> Someone already in the archive</label></div></fieldset>
  <div id="whoNew"><fieldset><legend>Their name</legend><div class="grid3">${fld("Given name", `<input name="given">`)}${fld("Patronymic", `<input name="patronymic">`)}${fld("Surname", `<input name="surname">`)}</div>
    <div class="grid2" style="margin-top:10px">${fld("Sex", `<select name="sex">${opt({unknown:"Unknown / not recorded", female:"Female", male:"Male", other:"Other"}, sexPreset)}</select>`)}${fld("Are they living?", `<select name="living">${opt({unknown:"Not sure", living:"Living", deceased:"Deceased"},"unknown")}</select>`)}</div></fieldset>
    <fieldset><legend>When and where were they born?</legend>${dateField("nbirth", null, "Birth date")}<div class="grid2" style="margin-top:10px">${placeInput("nbplace", null, "Birthplace")}${statusSelect("nbstatus")}</div></fieldset></div>
  <div id="whoExisting" hidden><fieldset>${fld("Choose person", `<select name="existing"><option value="">Choose…</option>${others.map(o=>`<option value="${o.id}">${esc(nameOf(o))} (${esc(yearsLine(o).text)})</option>`).join("")}</select>`)}</fieldset></div>
  <fieldset><legend>About the relationship</legend>${relFields}<details class="more" style="margin-top:12px"><summary>${t("Attach a source")}</summary>${citesField([])}</details></fieldset>`;
  openModal({title:t("Add "+REL_WORD[relation]+" of {name}",{name:nameOf(p)}), body, primary:t("Add"),
    onOpen:(root)=>{ $$('[name="who"]', root).forEach(r=>r.addEventListener("change", ()=>{ const ex = val(root,"who")==="existing"; $("#whoNew",root).hidden = ex; $("#whoExisting",root).hidden = !ex; })); },
    onPrimary:(root)=>{
      const mode = val(root,"who"); let other = null, newPerson = null, nb = null;
      if(mode==="existing"){ other = val(root,"existing"); if(!other) return "Choose a person, or switch to “Someone new”."; }
      else {
        const given = val(root,"given"), surname = val(root,"surname"), patronymic = val(root,"patronymic");
        if(!given && !surname) return "Enter at least a given name or surname. If the name is unknown, write what you know, e.g. given name “Unknown”, surname “Nurmatov”.";
        nb = readDate(root,"nbirth"); const e = validateDate(nb); if(e) return t("Birth date — {e}",{e});
        const living = val(root,"living");
        newPerson = {id:uid("p"), names:[{id:uid("nm"), type:"birth", given, patronymic, surname, full:"", script:"Latn", primary:true}], sex:val(root,"sex"), living, privacy: living==="deceased"?"family":"private", notes:"", resolutions:{}};
        other = newPerson.id;
      }
      const exists = (id)=> !!P(id) || (newPerson && newPerson.id===id);
      if(!exists(other)) return "That person no longer exists.";
      const status = val(root,"rstatus") || "unverified";
      const cites = readCites(root); if(cites.err) return cites.err;
      // validation against the existing graph
      if(isParent){
        if(!newPerson){ if(isAncestor(pid, other)) return t("{a} is a descendant of {b} — they can’t also be their parent.",{a:nameById(other), b:nameOf(p)}); if(parentsOf(pid).some(x=>x.person.id===other)) return "Already recorded as a parent."; }
        const nat = val(root,"nature"); if(nat==="biological" && parentsOf(pid).filter(x=>x.rel.nature==="biological").length>=2) return t("{name} already has two biological parents recorded. Record this person as another kind of parent, or edit the existing links first.",{name:nameOf(p)});
      }
      if(relation==="child" && !newPerson){ if(isAncestor(other, pid)) return t("{a} is an ancestor of {b} — they can’t also be their child.",{a:nameById(other), b:nameOf(p)}); if(childrenOf(pid).some(x=>x.person.id===other)) return "Already recorded as a child."; }
      if(relation==="partner" && !newPerson && unionsOf(pid).some(u=>u.partnerId===other)) return "These two are already recorded as partners. Edit the existing union instead.";
      let us, ue;
      if(relation==="partner"){ us = readDate(root,"ustart"); let e = validateDate(us); if(e) return t("Union date — {e}",{e}); ue = readDate(root,"uendd"); e = validateDate(ue); if(e) return t("End date — {e}",{e}); }
      // commit
      if(newPerson){ put("people", newPerson); const bp = val(root,"nbplace"); if(nb.mode!=="unknown" || bp) put("events", {id:uid("ev"), type:"birth", date:nb, placeId:placeIdFor(bp), participants:[{personId:newPerson.id, role:"principal"}], status:val(root,"nbstatus"), citations:[], title:"", description:""}); }
      const citations = cites.commit();
      if(isParent) put("rels", {id:uid("r"), type:"parentChild", parentId:other, childId:pid, nature:val(root,"nature"), status, citations, notes:""});
      if(relation==="child"){ put("rels", {id:uid("r"), type:"parentChild", parentId:pid, childId:other, nature:val(root,"nature"), status, citations, notes:""});
        const op = val(root,"otherParent"); if(op && !parentsOf(other).some(x=>x.person.id===op)) put("rels", {id:uid("r"), type:"parentChild", parentId:op, childId:other, nature:val(root,"nature"), status, citations:[], notes:""}); }
      if(relation==="partner") put("rels", {id:uid("r"), type:"union", aId:pid, bId:other, unionType:val(root,"utype"), start:us, startPlaceId:placeIdFor(val(root,"uplace")), endReason:val(root,"uend"), endDate:ue, status, citations});
      if(relation==="sibling"){
        const shared = $$('[name="sharedParent"]:checked', root).map(x=>x.value);
        if(shared.length) shared.forEach(par=>{ if(!parentsOf(other).some(x=>x.person.id===par)){ const src = parentsOf(pid).find(x=>x.person.id===par); put("rels", {id:uid("r"), type:"parentChild", parentId:par, childId:other, nature: src? src.rel.nature : "biological", status, citations: citations, notes:""}); } });
        else put("rels", {id:uid("r"), type:"sibling", aId:pid, bId:other, nature:val(root,"sibNature"), status, citations});
      }
      render(); toast(t("Added {name} as "+REL_WORD[relation]+".",{name:nameById(other)}));
    }});
}

/* ---------- events ---------- */
function openEventForm(pid, evId, presetType){
  const e = evId ? S.events[evId] : null; const creating = !e;
  const principal = e ? ((e.participants||[]).find(x=>x.role==="principal")||{}).personId : pid;
  const alsoIds = e ? (e.participants||[]).filter(x=>x.personId!==principal).map(x=>x.personId) : [];
  const ppl = Object.values(S.people).filter(x=>x.id!==principal).sort((a,b)=>nameOf(a).localeCompare(nameOf(b)));
  const body = `${placesDatalist()}
    <div class="grid2">${fld("What happened?", `<select name="type">${opt(EVENT_TYPES, e?e.type:(presetType||"residence"))}</select>`)}${fld("Short title (optional)", `<input name="title" value="${esc(e?e.title:"")}" placeholder="e.g. Moved to Tashkent for work">`)}</div>
    <p class="hint" id="singHint" hidden style="margin-top:8px"></p>
    <div style="margin-top:12px">${dateField("edate", e?e.date:null, "When")}</div>
    <div class="grid2" style="margin-top:12px">${placeInput("eplace", e?e.placeId:null, "Where")}<div id="toWrap">${placeInput("eto", e?e.toPlaceId:null, "Moved to")}</div></div>
    <div style="margin-top:12px">${fld("What do you know?", `<textarea name="desc" placeholder="Keep uncertain words like “around” or “we think”.">${esc(e?e.description:"")}</textarea>`)}</div>
    <div class="grid2" style="margin-top:12px">${statusSelect("status", e?e.status:"unverified")}${fld("Also involved (hold Ctrl/⌘ to pick several)", `<select name="also" multiple size="4">${ppl.map(x=>`<option value="${x.id}" ${alsoIds.includes(x.id)?"selected":""}>${esc(nameOf(x))}</option>`).join("")}</select>`)}</div>
    <div style="margin-top:12px">${citesField(e?e.citations:[])}</div>`;
  openModal({title: creating? t("Add an event for {name}",{name:nameById(principal)}) : t("Edit event"), body, primary: creating?"Add event":"Save changes",
    extra: creating? null : {label:"Delete event", fn:(root, close)=>{ if(!confirm(t("Delete this event? Its citations are removed too; the sources stay."))) return; const pr = principal; del("events", e.id); const pp = P(pr); if(pp && pp.resolutions && pp.resolutions[e.type] && pp.resolutions[e.type].eventId===e.id){ delete pp.resolutions[e.type]; put("people", pp); } close(); render(); toast("Event deleted."); }},
    onOpen:(root)=>{ const ty = $('[name="type"]', root); const upd = ()=>{ $("#toWrap",root).style.visibility = ty.value==="migration"?"visible":"hidden"; const h = $("#singHint",root); const n = vitalRecords(principal, ty.value).filter(x=>!e||x.id!==e.id).length; h.hidden = !(SINGULAR.includes(ty.value) && n); h.textContent = t("{name} already has {n} {what} record(s). Adding another records a second claim — if they disagree, the app flags a conflict and does not choose between them.",{name:nameById(principal), n, what:EVENT_TYPES[ty.value].toLowerCase()}); }; ty.addEventListener("change", upd); upd(); },
    onPrimary:(root)=>{
      const dt = readDate(root,"edate"); const er = validateDate(dt); if(er) return er;
      const type = val(root,"type"); const pl = val(root,"eplace"), to = type==="migration" ? val(root,"eto") : "";
      if(dt.mode==="unknown" && !pl && !val(root,"desc") && !val(root,"title")) return "Add at least a date, a place, a title or a description.";
      const b = vital(principal,"birth").chosen; if(b && b.date && dt.y && b.date.mode!=="unknown" && type!=="birth" && dt.mode!=="before" && dRange(dt) && dRange(b.date) && dRange(dt)[1] < dRange(b.date)[0]) return "This event is dated before the person's recorded birth. Check the date, or record it as a separate birth claim.";
      const c = readCites(root); if(c.err) return c.err;
      const also = [...$('[name="also"]', root).selectedOptions].map(o=>o.value);
      const obj = e || {id:uid("ev")};
      Object.assign(obj, {type, title:val(root,"title"), date:dt, placeId:placeIdFor(pl), toPlaceId:placeIdFor(to), description:val(root,"desc"), status:val(root,"status"), citations:c.commit(), participants:[{personId:principal, role:"principal"}, ...also.map(id=>({personId:id, role:"participant"}))]});
      put("events", obj); render(); toast(creating? "Event added." : "Saved.");
    }});
}

/* ---------- relationship edit ---------- */
function openRelForm(relId){
  const r = S.rels[relId]; if(!r) return;
  let body = "", title = "";
  if(r.type==="parentChild"){ title = `${nameById(r.parentId)} → ${nameById(r.childId)}`;
    body = `<p class="hint">${t("{a} is recorded as a parent of {b}.",{a:esc(nameById(r.parentId)), b:esc(nameById(r.childId))})}</p><div class="grid2">${fld("Type of link", `<select name="nature">${opt(PC_NATURE, r.nature)}</select>`)}${statusSelect("status", r.status)}</div><div style="margin-top:12px">${fld("Notes", `<textarea name="notes">${esc(r.notes||"")}</textarea>`)}</div><div style="margin-top:12px">${citesField(r.citations)}</div>`; }
  else if(r.type==="union"){ title = `${nameById(r.aId)} & ${nameById(r.bId)}`;
    body = `${placesDatalist()}<div class="grid2">${fld("Kind of union", `<select name="utype">${opt(UNION_TYPE, r.unionType)}</select>`)}${statusSelect("status", r.status)}</div><div style="margin-top:12px">${dateField("ustart", r.start, "Date of marriage or union")}</div>
     <div class="grid2" style="margin-top:12px">${placeInput("uplace", r.startPlaceId, "Where")}${fld("Did the union end?", `<select name="uend">${opt(UNION_END, r.endReason||"")}</select>`)}</div><div style="margin-top:12px">${dateField("uendd", r.endDate, "When it ended")}</div><div style="margin-top:12px">${citesField(r.citations)}</div>`; }
  else { title = `${nameById(r.aId)} & ${nameById(r.bId)}`;
    body = `<div class="grid2">${fld("Kind of sibling", `<select name="nature">${opt({unknown:"Sibling — details unknown", full:"Full sibling", half:"Half-sibling", step:"Step-sibling", adoptive:"Adoptive sibling"}, r.nature)}</select>`)}${statusSelect("status", r.status)}</div><div style="margin-top:12px">${citesField(r.citations)}</div>`; }
  openModal({title:"Edit relationship", sub:esc(title), body, primary:"Save changes",
    extra:{label:"Remove relationship", fn:(root, close)=>{ if(!confirm(t("Remove this relationship? Both people stay in the archive."))) return; del("rels", r.id); close(); render(); toast("Relationship removed."); }},
    onPrimary:(root)=>{
      const c = readCites(root); if(c.err) return c.err;
      if(r.type==="union"){ const s = readDate(root,"ustart"), en = readDate(root,"uendd"); let e = validateDate(s); if(e) return t("Union date — {e}",{e}); e = validateDate(en); if(e) return t("End date — {e}",{e}); Object.assign(r, {unionType:val(root,"utype"), start:s, startPlaceId:placeIdFor(val(root,"uplace")), endReason:val(root,"uend"), endDate:en}); }
      else { r.nature = val(root,"nature"); if(r.type==="parentChild") r.notes = val(root,"notes"); }
      if(r.type==="parentChild" && r.nature==="biological" && parentsOf(r.childId).filter(x=>x.rel.nature==="biological" && x.rel.id!==r.id).length>=2) return t("{name} already has two other biological parents recorded.",{name:nameById(r.childId)});
      r.status = val(root,"status"); r.citations = c.commit(); put("rels", r); render(); toast("Saved.");
    }});
}

/* ---------- conflicts ---------- */
function openPrefer(pid, type, evId){
  const e = S.events[evId]; const p = P(pid);
  openModal({title:"Choose a preferred record", size:"sm", sub:t("{type} of {name}: {date}",{type:esc(EVENT_TYPES[type]), name:esc(nameOf(p)), date:esc(fmtDate(e.date)||t("date unknown"))+(e.placeId?", "+esc(placeName(e.placeId)):"")}),
    body:`<p class="hint">The other record stays in the archive. Explain why this one is more reliable, so a future researcher can follow your reasoning.</p>${fld("Reason", `<textarea name="note" placeholder="e.g. The certificate was issued at the time; the interview recalls events 90 years later."></textarea>`)}`,
    primary:"Prefer this record",
    onPrimary:(root)=>{ const note = val(root,"note"); if(note.length<10) return "Write a short reason (at least a sentence)."; p.resolutions = p.resolutions||{}; p.resolutions[type] = {state:"preferred_selected", eventId:evId, note, at:nowISO()}; put("people", p); render(); toast("Preferred record saved. The conflict is marked resolved."); }});
}

/* ---------- sources & branches ---------- */
function openSourceForm(sid){
  const s = sid ? S.sources[sid] : null; const creating = !s;
  const cited = s ? allCitingItems(s.id) : [];
  const body = `${fld("Title", `<input name="title" value="${esc(s?s.title:"")}" placeholder="e.g. Birth certificate of …, Interview with …">`)}
    <div class="grid2" style="margin-top:12px">${fld("Type", `<select name="type">${opt(SOURCE_TYPES, s?s.type:"official_document")}</select>`)}${fld("Author, office or informant", `<input name="author" value="${esc(s?s.author||"":"")}">`)}</div>
    <div style="margin-top:12px">${dateField("sdate", s?s.date:null, "Date of the source")}</div>
    <div class="grid2" style="margin-top:12px">${fld("Reference / archive number", `<input name="reference" value="${esc(s?s.reference||"":"")}">`)}${fld("Web address (if online)", `<input name="url" type="url" value="${esc(s?s.url||"":"")}" placeholder="https://">`)}</div>
    <div style="margin-top:12px">${fld("Description", `<textarea name="description">${esc(s?s.description||"":"")}</textarea>`)}</div>
    <div style="margin-top:12px">${fld("Reliability notes", `<textarea name="reliability" placeholder="Original or copy? First-hand or remembered later? Known errors?">${esc(s?s.reliability||"":"")}</textarea>`)}</div>`;
  openModal({title: creating? "Add a source" : "Edit source", body, primary: creating? "Add source" : "Save changes",
    extra: creating? null : {label: cited.length? t("Delete (cited {n}×)",{n:cited.length}) : t("Delete source"), fn:(root, close)=>{
      if(cited.length && !confirm(t("This source supports {n} fact(s). Deleting it removes those citations — the facts stay, but lose their evidence. Continue?",{n:cited.length}))) return;
      if(!cited.length && !confirm(t("Delete this source?"))) return;
      cited.forEach(i=>{ i.obj.citations = i.obj.citations.filter(c=>c.sourceId!==s.id); put(i.kind, i.obj); }); del("sources", s.id); close(); render(); toast("Source deleted."); }},
    onPrimary:(root)=>{
      const title = val(root,"title"); if(!title) return "Give the source a title.";
      const url = val(root,"url"); if(url && !/^https?:\/\//i.test(url)) return "Web addresses must start with http:// or https://.";
      const d = readDate(root,"sdate"); const e = validateDate(d); if(e) return e;
      const obj = s || {id:uid("src")}; Object.assign(obj, {title, type:val(root,"type"), author:val(root,"author"), date:d, reference:val(root,"reference"), url, description:val(root,"description"), reliability:val(root,"reliability")});
      put("sources", obj); render(); toast(creating? "Source added." : "Saved.");
    }});
}
function openBranchForm(bid){
  const b = bid ? S.branches[bid] : null; const ppl = Object.values(S.people).sort((a,b)=>nameOf(a).localeCompare(nameOf(b)));
  if(!ppl.length){ toast("Add people first — a branch starts from a founder."); return; }
  openModal({title: b? "Edit branch" : "Add a branch", size:"sm",
    body:`${fld("Name", `<input name="name" value="${esc(b?b.name:"")}" placeholder="e.g. Karimov line">`)}<div style="margin-top:12px">${fld("Founder (branch = their descendants and partners)", `<select name="founder"><option value="">Choose…</option>${ppl.map(p=>`<option value="${p.id}" ${b&&b.founderId===p.id?"selected":""}>${esc(nameOf(p))} (${esc(yearsLine(p).text)})</option>`).join("")}</select>`)}</div><div style="margin-top:12px">${fld("Description", `<textarea name="description">${esc(b?b.description||"":"")}</textarea>`)}</div>`,
    primary: b? "Save changes" : "Add branch",
    extra: b? {label:"Delete branch", fn:(root, close)=>{ if(!confirm(t("Delete this branch? Nobody is removed from the archive."))) return; del("branches", b.id); close(); render(); }} : null,
    onPrimary:(root)=>{ const name = val(root,"name"), founderId = val(root,"founder"); if(!name) return "Name the branch."; if(!founderId) return "Choose the founder."; const o = b || {id:uid("br")}; Object.assign(o, {name, founderId, description:val(root,"description")}); put("branches", o); render(); toast("Branch saved."); }});
}

/* ---------- delete person ---------- */
function openDeletePerson(pid){
  const p = P(pid); const imp = impactOfDeleting(pid);
  openModal({title:t("Delete {name}?",{name:nameOf(p)}), size:"sm", primary:t("Delete person"),
    body:`<p>${t("This removes {name} from the archive, together with:",{name:esc(nameOf(p))})}</p><ul class="small">
      <li>${tn(imp.rels.length,"{n} relationship link (the other people stay)","{n} relationship links (the other people stay)")}</li>
      <li>${tn(imp.onlyTheirs.length,"{n} event that involves only them","{n} events that involve only them")}</li>
      ${imp.shared.length?`<li>${t("They are removed from {n} shared event(s), which are kept",{n:imp.shared.length})}</li>`:""}
      ${imp.branches.length?`<li>${t("{n} branch(es) founded by them",{n:imp.branches.length})}</li>`:""}
      <li>Sources are kept.</li></ul><p class="small muted">Download a backup first if you may want this later.</p>`,
    onPrimary:()=>{ const name = nameOf(p); deletePerson(pid); if(T.focusId===pid) T.focusId = (Object.values(S.people)[0]||{}).id || null; go("people"); toast(t("{name} deleted.",{name})); }});
}

/* ---------- menus ---------- */
function openMenu(anchor, items){
  $$(".menu").forEach(m=>m.remove());
  const m = document.createElement("div"); m.className = "menu"; m.setAttribute("role","menu");
  m.innerHTML = items.map((it,i)=>`<button role="menuitem" data-i="${i}">${esc(it[0])}</button>`).join("");
  document.body.appendChild(m); const r = anchor.getBoundingClientRect();
  m.style.top = (r.bottom + window.scrollY + 4) + "px"; m.style.left = Math.min(r.left, innerWidth - 210) + "px";
  const close = ()=>{ m.remove(); document.removeEventListener("click", outside, true); anchor.focus(); };
  const outside = (e)=>{ if(!m.contains(e.target)){ m.remove(); document.removeEventListener("click", outside, true); } };
  m.addEventListener("click", e=>{ const b = e.target.closest("[data-i]"); if(b){ close(); items[+b.dataset.i][1](); } });
  m.addEventListener("keydown", e=>{ const bs = $$("button", m); const i = bs.indexOf(document.activeElement); if(e.key==="ArrowDown"){ e.preventDefault(); bs[(i+1)%bs.length].focus(); } if(e.key==="ArrowUp"){ e.preventDefault(); bs[(i-1+bs.length)%bs.length].focus(); } if(e.key==="Escape") close(); });
  setTimeout(()=>{ document.addEventListener("click", outside, true); $("button", m).focus(); }, 0);
}

/* ---------- files: export / import ---------- */
let dlPromise = null;
async function saveFile(name, blob){
  if(!dlPromise) dlPromise = window.claude && window.claude.use ? window.claude.use("downloads") : Promise.resolve(null);
  const d = await dlPromise;
  if(d){ try{ const r = await d.save({filename:name, data:blob}); toast(r.status==="delivered" ? t("Sent.") : t("Saved {name}.",{name})); }
         catch(e){ toast(e.code==="declined" ? "Download cancelled." : e.code==="rate_limited" ? "A download prompt is already open." : t("Download failed: {e}",{e:e.message||e.code})); } return; }
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = name; document.body.appendChild(a); a.click(); a.remove(); setTimeout(()=>URL.revokeObjectURL(a.href), 8000);
  toast(t("Download started: {name}",{name}));
}
function exportData(mode){
  const out = {format:"family-archive", version:1, exportedAt:nowISO(), title:archiveTitle(), demo: WS==="demo", shareable: mode==="share"};
  KINDS.forEach(k=>{ out[k] = Object.values(clone(S[k])); });
  if(mode==="share"){
    const drop = new Set(out.people.filter(p=>p.living!=="living" && p.privacy==="private").map(p=>p.id));
    const livingIds = new Set(out.people.filter(p=>p.living!=="deceased").map(p=>p.id)); // unknown treated as living
    out.people = out.people.filter(p=>!drop.has(p.id)).map(p=> livingIds.has(p.id) ? {id:p.id, names:p.names.filter(n=>n.primary), sex:p.sex, living:p.living, privacy:p.privacy, redacted:true} : p);
    out.events = out.events.filter(e=>!(e.participants||[]).some(x=>drop.has(x.personId) || livingIds.has(x.personId)));
    out.rels = out.rels.filter(r=>![r.parentId,r.childId,r.aId,r.bId].some(id=>id && drop.has(id))).map(r=> r.type==="union" && (livingIds.has(r.aId)||livingIds.has(r.bId)) ? {...r, start:{mode:"unknown"}, startPlaceId:null, endDate:{mode:"unknown"}} : r);
  }
  const base = archiveTitle().replace(/[^\w\-]+/g,"-").toLowerCase().replace(/^-|-$/g,"") || "family-archive";
  saveFile(`${base}-${mode==="share"?"shareable":"backup"}-${nowISO().slice(0,10)}.json`, new Blob([JSON.stringify(out, null, 2)], {type:"application/json"}));
}
function validateImport(o){
  if(!o || o.format!=="family-archive") return {err:t("This file isn't a Family Archive backup (missing format marker).")};
  if(o.version!==1) return {err:t("This backup is version {v}; this app reads version 1.",{v:o.version})};
  const A = empty(); const warn = [];
  for(const k of KINDS){ if(o[k] && !Array.isArray(o[k])) return {err:t("The “{k}” section is malformed.",{k})}; (o[k]||[]).forEach(x=>{ if(x && typeof x.id==="string") A[k][x.id] = x; }); }
  for(const p of Object.values(A.people)){ if(!Array.isArray(p.names)) p.names = []; p.resolutions = p.resolutions||{}; }
  let dropped = 0;
  for(const r of Object.values(A.rels)){ const ids = [r.parentId,r.childId,r.aId,r.bId].filter(Boolean); if(ids.some(id=>!A.people[id])){ delete A.rels[r.id]; dropped++; } }
  for(const e of Object.values(A.events)){ e.participants = (e.participants||[]).filter(x=>A.people[x.personId]); if(!e.participants.length){ delete A.events[e.id]; dropped++; } e.citations = (e.citations||[]).filter(c=>A.sources[c.sourceId]); }
  if(dropped) warn.push(t("{n} record(s) referred to people missing from the file and were skipped.",{n:dropped}));
  if(o.shareable) warn.push(t("This is a shareable copy: living people's details were removed when it was made."));
  if(o.demo && WS==="mine") warn.push(t("This file was exported from the demo workspace — it contains fictional people."));
  return {A, warn};
}
async function handleImport(file){
  const msg = $("#importMsg"); msg.textContent = "";
  if(file.size > 50e6){ msg.textContent = "That file is larger than 50 MB — it isn't a backup from this app."; return; }
  let o; try{ o = JSON.parse(await file.text()); } catch(e){ msg.textContent = "The file couldn't be read as JSON. Choose a .json backup made by this app."; return; }
  const v = validateImport(o); if(v.err){ msg.textContent = v.err; return; }
  const n = Object.keys(v.A.people).length, cur = Object.keys(S.people).length;
  openModal({title:t("Restore this backup?"), size:"sm", primary: WS==="mine"? t("Replace my archive") : t("Load into demo"),
    body:`<p>${t("The backup contains {n} people, {e} events, {r} relationships and {s} sources.",{n, e:Object.keys(v.A.events).length, r:Object.keys(v.A.rels).length, s:Object.keys(v.A.sources).length})}</p>${v.warn.map(w=>`<p class="small err">${esc(w)}</p>`).join("")}<p class="small muted">${cur? t("This replaces the {n} people currently in this workspace.",{n:cur}) : ""}</p><p class="small" id="impProg" role="status"></p>`,
    onPrimary: async (root)=>{
      const prog = $("#impProg", root);
      if(WS==="mine"){
        prog.textContent = "Removing current records…"; await writeChain; await backend.wipe(S);
        const all = KINDS.flatMap(k=>Object.values(v.A[k]).map(x=>[k,x])); let i = 0;
        S = empty(); MINE.data = S;
        for(const [k,x] of all){ S[k][x.id] = x; await backend.put(k, clone(x)); if(++i % 10===0) prog.textContent = t("Writing {i} of {n}…",{i, n:all.length}); }
        prog.textContent = t("Restored {n} records.",{n:all.length});
      } else { S = v.A; DEMO_S = S; }
      T.focusId = pickDefaultFocus(); T.hasView = false; render(); toast("Backup restored.");
    }});
}

/* ---------- workspaces ---------- */
let DEMO_S = null;
function pickDefaultFocus(){ if(WS==="demo" && DEMO_ROOT && P(DEMO_ROOT)) return DEMO_ROOT; const ppl = Object.values(S.people).sort((a,b)=>String(a.created).localeCompare(String(b.created))); return ppl.length? ppl[0].id : null; }
async function openMine(){
  if(MINE || mineLoading || !ACC.cur) return;
  const acct = ACC.cur;
  mineLoading = true; updateSaveState(); if(WS==="mine") render();
  try{
    const b = accountBackend(acct);
    let data = await b.load(); if(!data) data = empty();
    if(ACC.cur!==acct){ mineLoading = false; return; }   // signed out meanwhile
    MINE = {backend:b, data};
  } catch(e){ mineError = e; MINE = {backend: MemoryBackend("Could not open your saved archive. Changes are not saved."), data: empty()}; console.error(e); }
  mineLoading = false;
  if(WS==="mine"){ S = MINE.data; backend = MINE.backend; T.focusId = pickDefaultFocus(); T.hasView = false; render(); }
  updateSaveState();
}
function switchWS(ws){
  if(ws===WS) return;
  if(ws==="mine" && !ACC.cur){ R.screen = "login"; LOGIN.tab = ACC.list.length ? "in" : "new"; go("login"); return; }
  WS = ws;
  if(ws==="demo"){ S = DEMO_S; backend = MemoryBackend("Demo"); }
  else { if(MINE){ S = MINE.data; backend = MINE.backend; } else { S = empty(); openMine(); } }
  T.focusId = pickDefaultFocus(); T.collapsed = new Set(); T.hasView = false; T.branchId = ""; T.unionId = "";
  go("dashboard"); render();
}
function onLangChanged(){
  const d = buildDemo(); DEMO_S = d.A; DEMO_ROOT = d.root;
  if(WS==="demo"){ S = DEMO_S; if(!P(T.focusId)) T.focusId = DEMO_ROOT; }
  T.hasView = false; render();
}

/* ---------- global event wiring ---------- */
document.addEventListener("click", e=>{
  const tt = e.target;
  const nav = tt.closest("[data-nav]"); if(nav){ go(nav.dataset.nav); return; }
  const ws = tt.closest("[data-ws]"); if(ws){ switchWS(ws.dataset.ws); return; }
  const gp = tt.closest("[data-go-person]"); if(gp && gp.dataset.goPerson && P(gp.dataset.goPerson)){ go("person", gp.dataset.goPerson); return; }
  const er = tt.closest("[data-edit-rel]"); if(er){ openRelForm(er.dataset.editRel); return; }
  const ee = tt.closest("[data-edit-event]"); if(ee){ openEventForm(null, ee.dataset.editEvent); return; }
  const pf = tt.closest("[data-pf]"); if(pf){ R.peopleF = pf.dataset.pf; render(); return; }
  const lg = tt.closest("[data-lang]"); if(lg){ setLang(lg.dataset.lang); return; }
  const tm = tt.closest("[data-tmode]"); if(tm){ T.mode = tm.dataset.tmode; T.hasView = false; if(T.mode==="branch" && !T.branchId) T.branchId = (Object.keys(S.branches)[0]||""); if(T.mode==="couple" && !T.unionId){ const u = unionsOf(T.focusId||"")[0]; T.unionId = u? u.rel.id : ""; } render(); return; }
  const a = tt.closest("[data-act]"); if(!a) return;
  const id = a.dataset.id;
  switch(a.dataset.act){
    case "rail": $("#rail").classList.toggle("open"); break;
    case "add-person": openPersonForm(null); break;
    case "edit-person": openPersonForm(id); break;
    case "delete-person": openDeletePerson(id); break;
    case "add-event": openEventForm(id, null, a.dataset.etype); break;
    case "change-pw": openChangePassword(); break;
    case "delete-account": openDeleteAccount(); break;
    case "add-rel": openAddRelative(id, a.dataset.rel); break;
    case "add-rel-menu": openMenu(a, [["Father",()=>openAddRelative(id,"father")],["Mother",()=>openAddRelative(id,"mother")],["Other parent (adoptive, step…)",()=>openAddRelative(id,"parent")],["Partner or spouse",()=>openAddRelative(id,"partner")],["Child",()=>openAddRelative(id,"child")],["Sibling",()=>openAddRelative(id,"sibling")]]); break;
    case "show-in-tree": T.focusId = id; if(!["family","ancestors","descendants"].includes(T.mode)) T.mode = "family"; T.hasView = false; go("tree"); break;
    case "prefer": openPrefer(id, a.dataset.type, a.dataset.ev); break;
    case "reopen-conflict": { const p = P(id); delete p.resolutions[a.dataset.type]; put("people", p); render(); toast("Conflict reopened."); break; }
    case "add-source": openSourceForm(null); break;
    case "edit-source": openSourceForm(id); break;
    case "add-branch": openBranchForm(null); break;
    case "edit-branch": openBranchForm(id); break;
    case "export-json": exportData(a.dataset.mode); break;
    case "export-tree": exportTree(a.dataset.fmt); break;
    case "legend-off": T.showLegend = false; render(); break;
    case "legend-on": T.showLegend = true; render(); break;
    case "save-title": { const v = $("#titleIn").value.trim(); if(!v){ toast("The title can't be empty."); break; } put("meta", {id:"archive", title:v, created:(S.meta.archive||{}).created}); render(); toast("Title saved."); break; }
    case "reset-demo": if(confirm(t("Discard your changes to the demo family?"))){ const d = buildDemo(); DEMO_S = d.A; DEMO_ROOT = d.root; S = DEMO_S; T.focusId = DEMO_ROOT; T.hasView = false; render(); toast("Demo reset."); } break;
    case "wipe": openModal({title:t("Delete my archive"), size:"sm", primary:t("Delete everything"), body:`<p>${t("This permanently deletes {n} people and every event, relationship, source and branch in your archive. It cannot be undone.",{n:Object.keys(S.people).length})}</p>${fld(t("Type {w} to confirm",{w:t("DELETE")}), '<input name="confirm" autocomplete="off">')}`,
      onPrimary: async (root)=>{ if(val(root,"confirm").toUpperCase()!==t("DELETE")) return t("Type {w} in capitals to confirm.",{w:t("DELETE")}); await writeChain; await backend.wipe(S); S = empty(); MINE.data = S; T.focusId = null; render(); toast(t("Your archive was deleted.")); }}); break;
  }
});
document.addEventListener("keydown", e=>{
  if(e.key==="Enter"){ const row = e.target.closest && e.target.closest("tr[data-go-person]"); if(row) go("person", row.dataset.goPerson); }
});
document.addEventListener("input", e=>{
  if(e.target.id==="pq"){ R.peopleQ = e.target.value; render(); const i = $("#pq"); i.focus(); i.setSelectionRange(i.value.length, i.value.length); }
});
document.addEventListener("change", e=>{
  const tt = e.target;
  if(tt.id==="tFocus"){ const hit = Object.values(S.people).find(p=>nameOf(p)===tt.value) || Object.values(S.people).find(p=>matchesName(p, tt.value)); if(hit){ T.focusId = hit.id; T.hasView = false; render(); setTimeout(()=>centerOn(hit.id, true), 30); } else toast(t("No one named “{name}”.",{name:tt.value})); }
  if(tt.id==="tUnion"){ T.unionId = tt.value; T.hasView = false; render(); }
  if(tt.id==="tBranch"){ T.branchId = tt.value; T.hasView = false; render(); }
  if(tt.id==="tUp"){ T.depthUp = +tt.value; T.hasView = false; render(); }
  if(tt.id==="tDown"){ T.depthDown = +tt.value; T.hasView = false; render(); }
  if(tt.id==="importFile" && tt.files[0]){ handleImport(tt.files[0]); tt.value = ""; }
});
window.addEventListener("hashchange", route);
let rz; window.addEventListener("resize", ()=>{ clearTimeout(rz); rz = setTimeout(()=>{ if(R.view==="tree" && svgEl) applyView(); }, 120); });

function isGuest(){ try{ return !!sessionStorage.getItem("fa:guest"); }catch(e){ return false; } }
/* ---------- init ---------- */
(async function init(){
  applyLang();
  const d = buildDemo(); DEMO_S = d.A; DEMO_ROOT = d.root; S = DEMO_S; T.focusId = DEMO_ROOT;
  render();                                   // "Opening…"
  await openAccountStore();
  if(ACC.cur){ WS = "mine"; R.screen = "app"; S = empty(); route(); openMine(); }
  else { R.screen = /^#\/(dashboard|tree|people|person|search|sources|settings)/.test(location.hash) && isGuest() ? "app" : "login"; route(); }
})();
