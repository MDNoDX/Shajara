"use strict";
/* =====================================================================
   CORE — vocabulary, fuzzy dates, store, backends, queries, evidence
   ===================================================================== */
const KINDS = ["people","events","rels","sources","places","branches","meta"];
const STATUS = {
  verified:{label:"Verified", icon:"✓", help:"Supported by a reliable source."},
  probable:{label:"Probable", icon:"◐", help:"Strong evidence, not fully verified."},
  family_tradition:{label:"Family tradition", icon:"❝", help:"Passed down orally in the family."},
  unverified:{label:"Unverified", icon:"?", help:"Claimed but not yet supported."},
  contradicted:{label:"Contradicted", icon:"!", help:"Sources disagree about this."}
};
const STATUS_RANK = {verified:4, probable:3, family_tradition:2, unverified:1, contradicted:0};
const PC_NATURE = {biological:"Biological", adoptive:"Adoptive", step:"Step", guardian:"Guardian", foster:"Foster", unknown:"Unknown / not stated"};
const UNION_TYPE = {marriage:"Marriage", religious_marriage:"Religious marriage (nikoh)", civil_partnership:"Civil partnership", partnership:"Partnership (unmarried)", unknown:"Unknown"};
const UNION_END = {"":"Still together / not ended", divorce:"Divorce", annulment:"Annulment", death:"Death of a partner", separation:"Separation", unknown:"Ended — reason unknown"};
const EVENT_TYPES = {birth:"Birth", death:"Death", burial:"Burial", education:"Education", employment:"Employment / occupation", military:"Military service", migration:"Migration / move", residence:"Residence", religious:"Religious event", achievement:"Achievement", travel:"Travel", family_event:"Family event", other:"Other"};
const SINGULAR = ["birth","death","burial"]; // types where >1 incompatible record = conflict
const NAME_TYPES = {birth:"Birth name", married:"Married name", former:"Former name", nickname:"Nickname", alternative:"Alternative spelling", historical:"Historical spelling", local_language:"Local-language form", arabic_script:"Arabic-script form", cyrillic:"Cyrillic / Russian form", other:"Other"};
const SCRIPTS = {Latn:"Latin", Cyrl:"Cyrillic", Arab:"Arabic", other:"Other"};
const SOURCE_TYPES = {official_document:"Official document", certificate:"Certificate", book:"Book", archive_record:"Archive record", website:"Website", interview:"Interview", family_member:"Family member (oral)", photograph:"Photograph", letter:"Letter", newspaper:"Newspaper", other:"Other"};
const PRIVACY = {private:"Private — only you", family:"Family — trusted family members", public:"Public — anyone with access"};
const MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
const DATE_MODES = {unknown:"Unknown", exact:"Exact date", month:"Month and year", year:"Year only", about:"About (circa)", before:"Before", after:"After", between:"Between"};

/* ---------- utilities ---------- */
const uid = (p) => p + "_" + Date.now().toString(36) + Math.random().toString(36).slice(2,8);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const nowISO = () => new Date().toISOString();
const clone = (o) => JSON.parse(JSON.stringify(o));
const $ = (s, r=document) => r.querySelector(s);
const $$ = (s, r=document) => [...r.querySelectorAll(s)];
const fold = (s) => String(s||"").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g,"").replace(/[ʻʼ'`‘’]/g,"");

/* ---------- fuzzy dates ----------
   {mode, y, m, d, y2, m2, d2, text}  — never forced to exact */
function one(y,m,d){ if(!y) return "?"; if(d && m) return `${d} ${MON[m-1]} ${y}`; if(m) return `${MON[m-1]} ${y}`; return `${y}`; }
function fmtDate(dt){
  if(!dt || !dt.mode || dt.mode==="unknown") return "";
  if(LANG==="uz") return fmtDateUz(dt);
  const a = one(dt.y,dt.m,dt.d);
  switch(dt.mode){
    case "exact": case "month": case "year": return a;
    case "about": return "c. " + a;
    case "before": return "before " + a;
    case "after": return "after " + a;
    case "between": return `between ${a} and ${one(dt.y2,dt.m2,dt.d2)}`;
  }
  return "";
}
function yearLabel(dt){
  if(!dt || !dt.mode || dt.mode==="unknown" || !dt.y) return null;
  if(LANG==="uz") return yearLabelUz(dt);
  switch(dt.mode){
    case "about": return "c." + dt.y;
    case "before": return "bef." + dt.y;
    case "after": return "aft." + dt.y;
    case "between": return dt.y===dt.y2 ? `${dt.y}` : `${dt.y}–${dt.y2}`;
    default: return `${dt.y}`;
  }
}
function dRange(dt){ // inclusive year range the claim allows; null if unknown
  if(!dt || !dt.mode || dt.mode==="unknown" || !dt.y) return null;
  switch(dt.mode){
    case "about": return [dt.y-2, dt.y+2];
    case "before": return [-Infinity, dt.y];
    case "after": return [dt.y, Infinity];
    case "between": return [dt.y, dt.y2||dt.y];
    default: return [dt.y, dt.y];
  }
}
function dSort(dt){ if(!dt || !dt.y || dt.mode==="unknown") return null; return dt.y*10000 + (dt.m||0)*100 + (dt.d||0); }
function dateCompatible(a,b){
  const ra=dRange(a), rb=dRange(b); if(!ra||!rb) return true;
  if(ra[1] < rb[0] || rb[1] < ra[0]) return false;
  if(a.mode==="exact" && b.mode==="exact" && (a.m!==b.m || a.d!==b.d)) return false;
  return true;
}
function validateDate(dt){
  if(!dt || dt.mode==="unknown") return null;
  const chk=(y,m,d,label)=>{
    if(!y || y<1000 || y>2100) return t("{label}: enter a four-digit year between 1000 and 2100.",{label:t(label)});
    if(m && (m<1||m>12)) return t("{label}: month must be 1–12.",{label:t(label)});
    if(d){ if(!m) return t("{label}: choose a month for the day.",{label:t(label)}); const max=new Date(y,m,0).getDate(); if(d<1||d>max) return t("{label}: {month} {y} has {max} days.",{label:t(label), month:MON[m-1], y, max}); }
    return null;
  };
  let e = chk(dt.y, dt.mode==="year"?null:dt.m, ["exact","about","before","after","between"].includes(dt.mode)?dt.d:null, "Date"); if(e) return e;
  if(dt.mode==="exact" && (!dt.m || !dt.d)) return t("Exact date needs day, month and year — or choose “Month and year” or “Year only”.");
  if(dt.mode==="month" && !dt.m) return t("Choose a month, or switch to “Year only”.");
  if(dt.mode==="between"){ e=chk(dt.y2,dt.m2,dt.d2,"End date"); if(e) return e; if((dSort({y:dt.y2,m:dt.m2,d:dt.d2,mode:"exact"})||0) < (dSort({...dt,mode:"exact"})||0)) return t("The end of the range is earlier than the start."); }
  const yNow = new Date().getFullYear(); if(dt.y > yNow+1) return t("That year is in the future.");
  return null;
}

/* ---------- state ---------- */
const empty = () => Object.fromEntries(KINDS.map(k=>[k,{}]));
let S = empty();
const P = (id) => S.people[id];

/* ---------- backends ----------
   memory (demo) · db (private per-user subtree on claude.ai) · local (browser) */
const MemoryBackend = (label) => ({ kind:"memory", label, async load(){ return null; }, async put(){}, async del(){}, async wipe(){} });

function LocalBackend(key){
  const KEY = key || "family-archive:mine:v1";
  const read = () => { try{ const v = localStorage.getItem(KEY); return v? JSON.parse(v) : null; }catch(e){ return null; } };
  const write = (o) => { localStorage.setItem(KEY, JSON.stringify(o)); };
  return {
    kind:"local", label:"Saved in this browser only — download a backup regularly",
    async load(){ const o = read() || empty(); KINDS.forEach(k=>{ o[k] = o[k] || {}; }); return o; },
    async put(k,obj){ const o = read() || empty(); o[k] = o[k]||{}; o[k][obj.id] = obj; write(o); },
    async del(k,id){ const o = read() || empty(); if(o[k]) delete o[k][id]; write(o); },
    async wipe(){ try{ localStorage.removeItem(KEY); }catch(e){} }
  };
}
/* db: the viewer's private subtree on claude.ai — data/users/<me>/<root>/<kind>/<id> */
function DbBackend(db, me, rootName){
  const root = db.doc(`data/users/${me}/${rootName}`);
  const col = (k) => root.collection(k);
  return {
    kind:"db", label:"Saved to your private space on claude.ai",
    async load(){
      const out = empty(); let truncated = false;
      for(const k of KINDS){
        const snap = await col(k).limit(1000).get();
        if(snap.docs.length === 1000) truncated = true;
        snap.docs.forEach(d=>{ const v = d.data(); if(v && v.id) out[k][v.id] = v; });
      }
      out.__truncated = truncated; return out;
    },
    async hasData(){ const snap = await col("people").limit(1).get(); return snap.docs.length > 0; },
    async put(k,obj){ await col(k).doc(obj.id).set(clone(obj)); },
    async del(k,id){ await col(k).doc(id).delete(); },
    async wipe(cur){ for(const k of KINDS) for(const id of Object.keys(cur[k]||{})) await col(k).doc(id).delete(); }
  };
}

/* single write queue: one write at a time, in order */
let writeChain = Promise.resolve(); let pending = 0; let lastError = null;
let backend = MemoryBackend("Demo");
function enqueue(fn){
  pending++; updateSaveState();
  writeChain = writeChain.then(fn).then(()=>{ lastError=null; }).catch(e=>{ lastError = e; console.error(e); })
    .finally(()=>{ pending--; updateSaveState(); });
  return writeChain;
}
function put(kind, obj){
  const t = nowISO(); obj.updated = t; if(!obj.created) obj.created = t;
  S[kind][obj.id] = obj;
  const b = backend; const copy = clone(obj);
  enqueue(()=>b.put(kind, copy));
  return obj;
}
function del(kind, id){ delete S[kind][id]; const b = backend; enqueue(()=>b.del(kind,id)); }

/* ---------- places (entity, found-or-created by name) ---------- */
function placeName(id){ return id && S.places[id] ? S.places[id].name : ""; }
function placeIdFor(name){
  name = String(name||"").trim(); if(!name) return null;
  const hit = Object.values(S.places).find(p=>fold(p.name)===fold(name));
  if(hit) return hit.id;
  return put("places", {id:uid("pl"), name}).id;
}

/* ---------- names ---------- */
function nameText(n){ if(!n) return ""; const parts=[n.given, n.patronymic, n.surname].filter(Boolean).join(" "); return parts || n.full || ""; }
function primaryNameObj(p){ return (p.names||[]).find(n=>n.primary) || (p.names||[])[0]; }
function nameOf(p){ if(!p) return t("Unknown person"); const s = nameText(primaryNameObj(p)); return s || t("Name not recorded"); }
function nameById(id){ return nameOf(P(id)); }
function initials(p){ const n = primaryNameObj(p); if(!n) return "?"; const a=(n.given||n.full||"?")[0]||"?"; const b=(n.surname||"")[0]||""; return (a+b).toUpperCase(); }
function nameVariants(p){ return (p.names||[]).flatMap(n=>[nameText(n), n.full].filter(Boolean)); }

/* ---------- relationships ---------- */
const rels = () => Object.values(S.rels);
function parentsOf(pid){ return rels().filter(r=>r.type==="parentChild" && r.childId===pid && P(r.parentId)).map(r=>({rel:r, person:P(r.parentId)})); }
function childrenOf(pid){ return rels().filter(r=>r.type==="parentChild" && r.parentId===pid && P(r.childId)).map(r=>({rel:r, person:P(r.childId)})); }
function unionsOf(pid){ return rels().filter(r=>r.type==="union" && (r.aId===pid||r.bId===pid)).map(r=>({rel:r, partnerId: r.aId===pid? r.bId : r.aId})).filter(u=>P(u.partnerId)); }
function explicitSiblings(pid){ return rels().filter(r=>r.type==="sibling" && (r.aId===pid||r.bId===pid)).map(r=>({rel:r, id: r.aId===pid? r.bId : r.aId})).filter(s=>P(s.id)); }
function siblingsOf(pid){
  const mine = parentsOf(pid).map(x=>x.person.id); const out = new Map();
  for(const par of mine){
    for(const c of childrenOf(par)){ if(c.person.id===pid) continue;
      const theirs = parentsOf(c.person.id).map(x=>x.person.id);
      const shared = mine.filter(x=>theirs.includes(x));
      let kind;
      if(shared.length>=2) kind="full";
      else if(mine.length>=2 && theirs.length>=2) kind="half";
      else kind="unclear";
      out.set(c.person.id, {id:c.person.id, kind, shared});
    }
  }
  for(const s of explicitSiblings(pid)) if(!out.has(s.id)) out.set(s.id, {id:s.id, kind:"recorded", rel:s.rel});
  return [...out.values()];
}
function isAncestor(a, b){ // is a an ancestor of b?
  const seen=new Set(); const st=[b];
  while(st.length){ const c=st.pop(); for(const {person} of parentsOf(c)){ if(person.id===a) return true; if(!seen.has(person.id)){ seen.add(person.id); st.push(person.id);} } }
  return false;
}

/* ---------- events & evidence ---------- */
const events = () => Object.values(S.events);
function eventsOf(pid){ return events().filter(e=>(e.participants||[]).some(x=>x.personId===pid)); }
function vitalRecords(pid, type){ return events().filter(e=>e.type===type && (e.participants||[]).some(x=>x.personId===pid && x.role==="principal")); }
function recordsCompatible(a,b){
  if(!dateCompatible(a.date,b.date)) return false;
  if(a.placeId && b.placeId && a.placeId!==b.placeId) return false;
  return true;
}
/* Returns {records, conflict:bool, resolution, chosen}
   chosen = the record to DISPLAY as the value, or null when an unresolved conflict exists. */
function vital(pid, type){
  const recs = vitalRecords(pid, type);
  let conflict = false;
  for(let i=0;i<recs.length;i++) for(let j=i+1;j<recs.length;j++) if(!recordsCompatible(recs[i],recs[j])) conflict = true;
  const res = ((P(pid)||{}).resolutions||{})[type];
  const resolved = conflict && res && res.state==="preferred_selected" && recs.some(r=>r.id===res.eventId) ? res : null;
  let chosen = null;
  if(!recs.length) chosen = null;
  else if(conflict) chosen = resolved ? recs.find(r=>r.id===resolved.eventId) : null;
  else chosen = [...recs].sort((a,b)=>(STATUS_RANK[b.status]||0)-(STATUS_RANK[a.status]||0) || specificity(b.date)-specificity(a.date))[0];
  return {records:recs, conflict, resolution:resolved, chosen};
}
function specificity(dt){ return !dt||dt.mode==="unknown"?0 : {exact:6,month:5,year:4,between:3,about:2,before:1,after:1}[dt.mode]||0; }
function yearsLine(p){
  const b = vital(p.id,"birth"), d = vital(p.id,"death");
  const part = (v) => {
    if(v.conflict && !v.chosen){ const ys=[...new Set(v.records.map(r=>yearLabel(r.date)||"?"))]; return {t: ys.join(" / "), conflict:true}; }
    return {t: v.chosen ? (yearLabel(v.chosen.date) || "?") : "?", conflict:false};
  };
  const bb = part(b), dd = part(d);
  let t0;
  if(p.living==="living") t0 = bb.t==="?" ? t("Living") : t("b. {y}",{y:bb.t});
  else if(p.living==="deceased") t0 = `${bb.t} – ${dd.t}`;
  else t0 = (!d.records.length) ? (bb.t==="?" ? t("Dates unknown") : t("b. {y}",{y:bb.t})) : `${bb.t} – ${dd.t}`;
  return {text:t0, conflict: bb.conflict||dd.conflict};
}
function unresolvedConflicts(pid){ return SINGULAR.filter(t=>{ const v=vital(pid,t); return v.conflict && !v.resolution; }); }
function citationsOf(o){ return (o.citations||[]).filter(c=>S.sources[c.sourceId]); }
function allCitingItems(sourceId){
  const out=[];
  for(const e of events()) if((e.citations||[]).some(c=>c.sourceId===sourceId)) out.push({kind:"events", obj:e});
  for(const r of rels()) if((r.citations||[]).some(c=>c.sourceId===sourceId)) out.push({kind:"rels", obj:r});
  return out;
}
function describeEvent(e){
  const who = (e.participants||[]).filter(x=>x.role==="principal").map(x=>nameById(x.personId)).join(", ");
  return who ? t("{type} of {who}",{type:EVENT_TYPES[e.type]||t("Event"), who}) : (EVENT_TYPES[e.type]||t("Event"));
}
function describeRel(r){
  if(r.type==="parentChild") return t("{a} → parent of {b} ({nature})",{a:nameById(r.parentId), b:nameById(r.childId), nature:(PC_NATURE[r.nature]||"").toLowerCase()});
  if(r.type==="union") return `${UNION_TYPE[r.unionType]||t("Union")}: ${nameById(r.aId)} & ${nameById(r.bId)}`;
  return t("Siblings: {a} & {b}",{a:nameById(r.aId), b:nameById(r.bId)});
}

/* ---------- generations ---------- */
function generationInfo(){
  const gen = new Map(); let maxSpan = 0;
  for(const p of Object.values(S.people)){
    if(gen.has(p.id)) continue;
    const comp = new Map([[p.id,0]]); const q=[p.id];
    while(q.length){ const c=q.shift(); const g=comp.get(c);
      for(const x of parentsOf(c)) if(!comp.has(x.person.id)){ comp.set(x.person.id,g-1); q.push(x.person.id); }
      for(const x of childrenOf(c)) if(!comp.has(x.person.id)){ comp.set(x.person.id,g+1); q.push(x.person.id); }
      for(const u of unionsOf(c)) if(!comp.has(u.partnerId)){ comp.set(u.partnerId,g); q.push(u.partnerId); }
    }
    const min = Math.min(...comp.values()), max = Math.max(...comp.values());
    for(const [id,g] of comp) gen.set(id, g-min+1);
    maxSpan = Math.max(maxSpan, max-min+1);
  }
  return {gen, count: Object.keys(S.people).length ? maxSpan : 0};
}

/* ---------- kinship label relative to a focus person ---------- */
function ancDist(pid){ const m=new Map([[pid,0]]); const q=[pid]; while(q.length){ const c=q.shift(); for(const {person} of parentsOf(c)) if(!m.has(person.id)){ m.set(person.id, m.get(c)+1); q.push(person.id);} } return m; }
const gw = (sx, male, female, neutral) => sx==="male"?male : sx==="female"?female : neutral;
function greats(n){ return n<=0 ? "" : n===1 ? "Great-" : n===2 ? "Great-great-" : `${n}× great-`; }
function ordinal(n){ return ["","First","Second","Third","Fourth","Fifth","Sixth"][n] || `${n}th`; }
function bloodLabel(focus, pid){
  if(focus===pid) return "Focus";
  const A=ancDist(focus), B=ancDist(pid); let best=null;
  for(const [id,a] of A) if(B.has(id)){ const b=B.get(id); if(!best || a+b < best.a+best.b) best={a,b}; }
  if(!best) return null;
  const {a,b} = best; const sx = (P(pid)||{}).sex;
  if(b===0){ if(a===1) return gw(sx,"Father","Mother","Parent"); return greats(a-2) + (a-2>0? gw(sx,"grandfather","grandmother","grandparent") : gw(sx,"Grandfather","Grandmother","Grandparent")); }
  if(a===0){ if(b===1) return gw(sx,"Son","Daughter","Child"); return greats(b-2) + (b-2>0? gw(sx,"grandson","granddaughter","grandchild") : gw(sx,"Grandson","Granddaughter","Grandchild")); }
  if(a===1 && b===1){ const s = siblingsOf(focus).find(x=>x.id===pid); const half = s && s.kind==="half"; return (half?"Half-":"") + (half? gw(sx,"brother","sister","sibling") : gw(sx,"Brother","Sister","Sibling")); }
  if(b===1){ const g=a-2; return g>0 ? greats(g) + gw(sx,"uncle","aunt","aunt/uncle") : gw(sx,"Uncle","Aunt","Aunt/uncle"); }
  if(a===1){ const g=b-2; return g>0 ? (g>1? greats(g-1)+"grand-" : "Grand-") + gw(sx,"nephew","niece","nephew/niece") : gw(sx,"Nephew","Niece","Nephew/niece"); }
  const deg = Math.min(a,b)-1, rem = Math.abs(a-b);
  return `${ordinal(deg)} cousin` + (rem? ` ${rem===1?"once":rem===2?"twice":rem+"×"} removed` : "");
}
function kinLabel(focus, pid){
  if(!focus || !P(focus)) return "";
  if(LANG==="uz") return kinUz(focus, pid);
  const bl = bloodLabel(focus, pid); if(bl) return bl==="Focus" ? "" : bl;
  const sx = (P(pid)||{}).sex;
  const u = unionsOf(focus).find(u=>u.partnerId===pid);
  if(u){ const former = u.rel.endReason && u.rel.endReason!=="death"; const w = u.rel.unionType==="partnership" ? "Partner" : gw(sx,"Husband","Wife","Spouse"); return former? "Former " + w.toLowerCase() : w; }
  for(const pu of unionsOf(pid)){
    const l = bloodLabel(focus, pu.partnerId); if(!l || l==="Focus") continue;
    if(/^(Son|Daughter|Child)$/.test(l)) return gw(sx,"Son-in-law","Daughter-in-law","Child-in-law");
    if(/(Brother|Sister|Sibling)$/i.test(l)) return gw(sx,"Brother-in-law","Sister-in-law","Sibling-in-law");
    if(/^(Uncle|Aunt)/.test(l)) return gw(sx,"Uncle by marriage","Aunt by marriage","By marriage (aunt/uncle)");
    return `${l}'s ${gw(sx,"husband","wife","spouse")}`;
  }
  for(const fu of unionsOf(focus)){ const d = ancDist(fu.partnerId).get(pid); if(d===1) return gw(sx,"Father-in-law","Mother-in-law","Parent-in-law"); }
  return "";
}

/* ---------- branches ---------- */
function branchMembers(bid){
  const b = S.branches[bid]; if(!b || !P(b.founderId)) return new Set();
  const set = new Set(); const st=[b.founderId];
  while(st.length){ const c=st.pop(); if(set.has(c)) continue; set.add(c); childrenOf(c).forEach(x=>st.push(x.person.id)); }
  [...set].forEach(id=>unionsOf(id).forEach(u=>set.add(u.partnerId)));
  return set;
}
function branchesOf(pid){ return Object.values(S.branches).filter(b=>branchMembers(b.id).has(pid)); }

/* ---------- integrity: deleting a person ---------- */
function impactOfDeleting(pid){
  const r = rels().filter(x=>x.parentId===pid||x.childId===pid||x.aId===pid||x.bId===pid);
  const ev = eventsOf(pid);
  const onlyTheirs = ev.filter(e=>(e.participants||[]).every(x=>x.personId===pid));
  const shared = ev.filter(e=>!onlyTheirs.includes(e));
  const br = Object.values(S.branches).filter(b=>b.founderId===pid);
  return {rels:r, onlyTheirs, shared, branches:br};
}
function deletePerson(pid){
  const imp = impactOfDeleting(pid);
  imp.rels.forEach(r=>del("rels", r.id));
  imp.onlyTheirs.forEach(e=>del("events", e.id));
  imp.shared.forEach(e=>{ e.participants = e.participants.filter(x=>x.personId!==pid); put("events", e); });
  imp.branches.forEach(b=>del("branches", b.id));
  del("people", pid);
}
