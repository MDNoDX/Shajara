"use strict";
/* =====================================================================
   I18N — Uzbek (default) and English.
   Source strings are English; UZ maps them to Uzbek. Static UI text is
   translated by a DOM pass (MutationObserver); dynamic text uses t().
   ===================================================================== */
let LANG = (()=>{ try{ return localStorage.getItem("family-archive:lang") || "uz"; }catch(e){ return "uz"; } })();
const LANGS = {uz:"O‘zbekcha", en:"English"};
function t(s, v){
  let o = (LANG==="uz" && UZ[s]!=null) ? UZ[s] : s;
  if(v) o = o.replace(/\{(\w+)\}/g, (m,k)=> v[k]!=null ? v[k] : m);
  return o;
}
const tg = (s, v) => t(s, v);
function tn(n, one, many, v){ return t(n===1? one : many, Object.assign({n}, v||{})); }

/* ---------- DOM localizer ---------- */
const LOC_SKIP = new Set(["SCRIPT","STYLE","TEXTAREA","CODE","PRE"]);
const LOC_ATTRS = ["placeholder","aria-label","title","alt"];
function locText(n){
  const p = n.parentNode; if(p && (LOC_SKIP.has(p.nodeName) || (p.closest && p.closest('[translate="no"]')))) return;
  const s = n.data; const k = s.trim(); if(!k || k.length>600) return;
  const v = UZ[k]; if(v!=null && v!==k) n.data = s.replace(k, ()=>v);
}
function locAttrs(el){
  if(!el.getAttribute) return;
  for(const a of LOC_ATTRS){ const v = el.getAttribute(a); if(v){ const k = v.trim(); const u = UZ[k]; if(u!=null && u!==k) el.setAttribute(a, u); } }
}
function locNode(root){
  if(LANG!=="uz" || !root) return;
  if(root.nodeType===3){ locText(root); return; }
  if(root.nodeType!==1) return;
  if(LOC_SKIP.has(root.nodeName) || (root.closest && root.closest('[translate="no"]'))) return;
  locAttrs(root);
  const w = document.createTreeWalker(root, NodeFilter.SHOW_ELEMENT|NodeFilter.SHOW_TEXT, {acceptNode(n){
    if(n.nodeType===1) return (LOC_SKIP.has(n.nodeName) || n.getAttribute("translate")==="no") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT;
    return NodeFilter.FILTER_ACCEPT; }});
  let n; while((n = w.nextNode())){ if(n.nodeType===3) locText(n); else locAttrs(n); }
}
function locString(svg){ // localize an SVG string built for export
  if(LANG!=="uz") return svg;
  try{ const d = new DOMParser().parseFromString(svg, "image/svg+xml"); const w = d.createTreeWalker(d.documentElement, 4); let n; while((n = w.nextNode())){ const k = n.data.trim(); if(k && UZ[k]!=null) n.data = n.data.replace(k, ()=>UZ[k]); } return new XMLSerializer().serializeToString(d); }
  catch(e){ return svg; }
}
const locObserver = new MutationObserver(ms=>{ if(LANG!=="uz") return; for(const m of ms) for(const n of m.addedNodes) locNode(n); });
locObserver.observe(document.documentElement, {childList:true, subtree:true});

/* ---------- constants: keep English originals, swap in translations ---------- */
let I18N_ORIG = null;
function applyLang(){
  const tables = {STATUS, PC_NATURE, UNION_TYPE, UNION_END, EVENT_TYPES, NAME_TYPES, SCRIPTS, SOURCE_TYPES, PRIVACY, DATE_MODES};
  if(!I18N_ORIG) I18N_ORIG = {tables: JSON.parse(JSON.stringify(tables)), MON: MON.slice()};
  for(const [name, obj] of Object.entries(tables)){
    const o = I18N_ORIG.tables[name];
    for(const k of Object.keys(o)){
      if(typeof o[k]==="string") obj[k] = t(o[k]);
      else { obj[k].label = t(o[k].label); obj[k].help = t(o[k].help); }
    }
  }
  const mon = LANG==="uz" ? UZ_MONTHS : I18N_ORIG.MON; mon.forEach((m,i)=>MON[i]=m);
  document.documentElement.lang = LANG;
  document.title = t("Family Archive");
}
function setLang(l){
  if(!LANGS[l] || l===LANG) return;
  LANG = l; try{ localStorage.setItem("family-archive:lang", l); }catch(e){}
  applyLang();
  if(typeof onLangChanged==="function") onLangChanged();
}
function langSwitchHTML(cls=""){
  return `<div class="langsw ${cls}" role="group" aria-label="Til / Language">${Object.entries(LANGS).map(([k,l])=>`<button data-lang="${k}" aria-pressed="${LANG===k}" translate="no">${l}</button>`).join("")}</div>`;
}

/* ---------- Uzbek dates ---------- */
const UZ_MONTHS = ["yanvar","fevral","mart","aprel","may","iyun","iyul","avgust","sentabr","oktabr","noyabr","dekabr"];
function uzBase(y,m,d){ if(!y) return "?"; if(d && m) return `${y}-yil ${d}-${UZ_MONTHS[m-1]}`; if(m) return `${y}-yil ${UZ_MONTHS[m-1]}`; return `${y}-yil`; }
function uzPlain(y,m,d){ if(!y) return "?"; if(d && m) return `${y}-yil ${d}-${UZ_MONTHS[m-1]}`; if(m) return `${y}-yil ${UZ_MONTHS[m-1]}`; return `${y}`; }
function fmtDateUz(dt){
  switch(dt.mode){
    case "exact": case "month": case "year": return uzPlain(dt.y,dt.m,dt.d);
    case "about": return "taxminan " + uzBase(dt.y,dt.m,dt.d);
    case "before": return uzBase(dt.y,dt.m,dt.d) + "dan oldin";
    case "after": return uzBase(dt.y,dt.m,dt.d) + "dan keyin";
    case "between": return `${uzBase(dt.y,dt.m,dt.d)} va ${uzBase(dt.y2,dt.m2,dt.d2)} oralig‘ida`;
  }
  return "";
}
function yearLabelUz(dt){
  switch(dt.mode){
    case "about": return "~" + dt.y;
    case "before": return dt.y + " gacha";
    case "after": return dt.y + " dan so‘ng";
    case "between": return dt.y===dt.y2 ? `${dt.y}` : `${dt.y}–${dt.y2}`;
    default: return `${dt.y}`;
  }
}

/* ---------- Uzbek kinship (possessive: "Otasi" = their father) ---------- */
function birthKey(pid){ const v = vital(pid,"birth"); const r = v.chosen || (v.records.length===1? v.records[0] : null); return r ? dSort(r.date) : null; }
function commonAncestor(focus, pid){
  const A = ancDist(focus), B = ancDist(pid); let best = null;
  for(const [id,a] of A) if(B.has(id)){ const b = B.get(id); if(!best || a+b < best.a+best.b) best = {a,b,id}; }
  return best;
}
function pathParent(from, ca, dist){ // the parent of `from` that lies on the path to ancestor `ca`
  for(const {person} of parentsOf(from)){ const d = ancDist(person.id).get(ca); if(d===dist-1) return person; }
  return null;
}
function bloodUz(focus, pid){
  if(focus===pid) return "Focus";
  const best = commonAncestor(focus, pid); if(!best) return null;
  const {a,b,id:ca} = best; const sx = (P(pid)||{}).sex;
  if(b===0){
    if(a===1) return gw(sx,"Otasi","Onasi","Ota-onasi");
    if(a===2) return gw(sx,"Bobosi","Buvisi","Bobosi / buvisi");
    if(a===3) return gw(sx,"Katta bobosi","Katta buvisi","Katta bobosi / buvisi");
    return gw(sx,`Bobokaloni (${a}-avlod)`,`Momokaloni (${a}-avlod)`,`Ajdodi (${a}-avlod)`);
  }
  if(a===0){
    if(b===1) return gw(sx,"O‘g‘li","Qizi","Farzandi");
    return ["","","Nabirasi","Evarasi","Chevarasi"][b] || `Avlodi (${b}-avlod)`;
  }
  if(a===1 && b===1){
    const s = siblingsOf(focus).find(x=>x.id===pid);
    let pre = "";
    if(s && s.kind==="half"){ const sp = P(s.shared[0]); pre = sp && sp.sex==="male" ? "Ota bir " : sp && sp.sex==="female" ? "Ona bir " : "O‘gay "; }
    const kp = birthKey(pid), kf = birthKey(focus);
    const older = kp!=null && kf!=null ? (kp < kf ? true : kp > kf ? false : null) : null;
    let w;
    if(sx==="male") w = older===true ? "akasi" : older===false ? "ukasi" : "aka-ukasi";
    else if(sx==="female") w = older===true ? "opasi" : older===false ? "singlisi" : "opa-singlisi";
    else w = "tug‘ishgani";
    const out = pre + w; return out[0].toUpperCase() + out.slice(1);
  }
  if(b===1){ // aunt / uncle
    if(a===2){
      const par = pathParent(focus, ca, a);
      if(par && par.sex==="male") return gw(sx,"Amakisi","Ammasi","Amakisi / ammasi");
      if(par && par.sex==="female") return gw(sx,"Tog‘asi","Xolasi","Tog‘asi / xolasi");
      return gw(sx,"Amaki / tog‘asi","Amma / xolasi","Qarindoshi");
    }
    return gw(sx,"Katta amaki / tog‘asi","Katta amma / xolasi","Katta qarindoshi");
  }
  if(a===1){ return b===2 ? "Jiyani" : b===3 ? "Jiyanining farzandi" : "Jiyanining avlodi"; }
  if(a===2 && b===2){
    const pf = pathParent(focus, ca, a), pp = pathParent(pid, ca, b);
    if(pf && pp && pf.sex && pp.sex && pf.sex!=="unknown" && pp.sex!=="unknown"){
      if(pf.sex==="male") return pp.sex==="male" ? "Amakivachchasi" : "Ammavachchasi";
      return pp.sex==="male" ? "Tog‘avachchasi" : "Xolavachchasi";
    }
    return "Amakivachcha / xolavachchasi";
  }
  return `Uzoq qarindoshi (${Math.min(a,b)-1}-daraja)`;
}
function kinUz(focus, pid){
  const bl = bloodUz(focus, pid); if(bl) return bl==="Focus" ? "" : bl;
  const sx = (P(pid)||{}).sex;
  const u = unionsOf(focus).find(u=>u.partnerId===pid);
  if(u){ const former = u.rel.endReason && u.rel.endReason!=="death";
    const w = u.rel.unionType==="partnership" ? "sherigi" : gw(sx,"eri","xotini","turmush o‘rtog‘i");
    return former ? "Sobiq " + w : w[0].toUpperCase()+w.slice(1); }
  for(const pu of unionsOf(pid)){
    const l = bloodUz(focus, pu.partnerId); if(!l || l==="Focus") continue;
    if(/^(O‘g‘li|Qizi|Farzandi)$/.test(l)) return gw(sx,"Kuyovi","Kelini","Kuyovi / kelini");
    if(sx==="female" && /(akasi|ukasi|aka-ukasi)$/.test(l)) return "Yangasi";
    if(sx==="male" && /(opasi|singlisi|opa-singlisi)$/.test(l)) return "Pochchasi";
    return `${l}ning ${gw(sx,"eri","xotini","turmush o‘rtog‘i")}`;
  }
  for(const fu of unionsOf(focus)){ const d = ancDist(fu.partnerId).get(pid); if(d===1) return gw(sx,"Qaynotasi","Qaynonasi","Qayn ota-onasi"); }
  return "";
}

/* ---------- parent role wording ---------- */
function parentRole(nature, sex){
  if(LANG==="uz"){
    const base = {biological:["Ota","Ona","Ota-ona"], adoptive:["Asrab olgan ota","Asrab olgan ona","Asrab olgan ota-ona"], step:["O‘gay ota","O‘gay ona","O‘gay ota-ona"], guardian:["Vasiy","Vasiy","Vasiy"], foster:["Tarbiyalagan ota","Tarbiyalagan ona","Tarbiyachi"], unknown:["Ota (turi noma’lum)","Ona (turi noma’lum)","Ota-ona (turi noma’lum)"]}[nature] || ["Ota","Ona","Ota-ona"];
    return sex==="male"? base[0] : sex==="female"? base[1] : base[2];
  }
  const w = sex==="male"?"father":sex==="female"?"mother":"parent";
  return nature==="biological" ? w[0].toUpperCase()+w.slice(1) : `${PC_NATURE[nature]} ${w}`;
}

/* ---------- demo data in Uzbek ---------- */
function localizeDemo(A){
  if(LANG!=="uz") return A;
  const tr = (s) => { if(typeof s!=="string" || !s) return s; if(DEMO_UZ[s]!=null) return DEMO_UZ[s];
    let m = s.match(/^p\. (\d+)$/); if(m) return `${m[1]}-bet`;
    m = s.match(/^entry (\d+)$/); if(m) return `${m[1]}-yozuv`;
    m = s.match(/^record (\d+)$/); if(m) return `${m[1]}-yozuv`;
    return s; };
  Object.values(A.places).forEach(p=>p.name = tr(p.name));
  Object.values(A.sources).forEach(s=>["title","author","reference","reliability","description"].forEach(k=>s[k]=tr(s[k])));
  Object.values(A.events).forEach(e=>{ e.title = tr(e.title); e.description = tr(e.description); (e.citations||[]).forEach(c=>c.detail = tr(c.detail)); });
  Object.values(A.rels).forEach(r=>(r.citations||[]).forEach(c=>c.detail = tr(c.detail)));
  Object.values(A.people).forEach(p=>{ p.notes = tr(p.notes); (p.names||[]).forEach(n=>{ if(n.full) n.full = tr(n.full); }); });
  Object.values(A.branches).forEach(b=>{ b.name = tr(b.name); b.description = tr(b.description); });
  Object.values(A.meta).forEach(m=>{ if(m.title) m.title = tr(m.title); });
  return A;
}
