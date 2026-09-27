/* =====================================================================
   DEMO DATA — a fictional family. None of these people are real.
   Kept in its own in-memory workspace; never written to "My archive".
   ===================================================================== */
function buildDemo(){
  const A = empty(); const T = "2026-01-01T00:00:00.000Z"; let seq = 0;
  const stamp = () => new Date(Date.parse(T) + (seq++)*3600e3).toISOString();
  const pl = {}; const place = (name) => { if(!pl[name]){ const id="dpl_"+Object.keys(pl).length; pl[name]=id; A.places[id]={id,name,created:stamp(),updated:T}; } return pl[name]; };
  const src = (id, o) => { A.sources[id] = {id, ...o, created:stamp(), updated:T}; };
  src("ds1",{title:"Birth certificate of Karim Nurmatov (demo)", type:"certificate", author:"Civil registry office, Namangan", date:{mode:"year",y:1928}, reference:"Reissued copy, entry 214", reliability:"Reissued in 1956 from the registry book, not the original 1928 entry — a copying error is possible.", description:"Fictional document for demonstration."});
  src("ds2",{title:"Interview with Rustam Nurmatov (demo)", type:"interview", author:"Recorded by Timur Nurmatov", date:{mode:"exact",y:2024,m:3,d:9}, reliability:"First-hand for events after 1960; earlier events are what his parents told him.", description:"Fictional oral-history interview, about 90 minutes."});
  src("ds3",{title:"Marriage certificate: Karim Nurmatov & Malika Qodirova (demo)", type:"certificate", author:"Civil registry office, Tashkent", date:{mode:"exact",y:1952,m:9,d:14}, reference:"Record no. 1187", reliability:"Original document held by the family.", description:"Fictional document."});
  src("ds4",{title:"Family notebook kept by Zulfiya Nurmatova (demo)", type:"letter", author:"Zulfiya Nurmatova", date:{mode:"between",y:1950,y2:1974}, reliability:"Written from memory decades after some events; dates for the 1920s–30s are approximate.", description:"Fictional handwritten notebook in Arabic script and later Cyrillic."});
  src("ds5",{title:"Adoption decision, district court (demo)", type:"official_document", author:"District court, Tashkent", date:{mode:"year",y:1985}, reliability:"Official record.", description:"Fictional document. Biological parents are not named in the record."});

  const people = {};
  const person = (key, o) => {
    const id = "dp_"+key;
    const names = (o.names||[]).map((n,i)=>({id:`dn_${key}_${i}`, type:n.type||"birth", given:n.given||"", patronymic:n.patronymic||"", surname:n.surname||"", full:n.full||"", script:n.script||"Latn", primary:i===0}));
    A.people[id] = {id, names, sex:o.sex, living:o.living, privacy:o.living==="living"?"private":"family", notes:o.notes||"", resolutions:o.resolutions||{}, created:stamp(), updated:T};
    people[key]=id; return id;
  };
  const ev = (type, pk, o) => { const id = "de_"+(seq); A.events[id] = {id, type, date:o.date||{mode:"unknown"}, placeId:o.place?place(o.place):null, toPlaceId:o.to?place(o.to):null, title:o.title||"", description:o.desc||"", participants:[{personId:people[pk], role:"principal"}].concat((o.with||[]).map(k=>({personId:people[k], role:"participant"}))), status:o.status||"unverified", citations:(o.cite||[]).map(c=>({sourceId:c[0], detail:c[1]||""})), created:stamp(), updated:T}; return id; };
  const pc = (par, ch, o={}) => { const id="dr_"+(seq); A.rels[id] = {id, type:"parentChild", parentId:people[par], childId:people[ch], nature:o.nature||"biological", status:o.status||"probable", citations:(o.cite||[]).map(c=>({sourceId:c[0], detail:c[1]||""})), notes:o.notes||"", created:stamp(), updated:T}; };
  const un = (a, b, o={}) => { const id="dr_"+(seq); A.rels[id] = {id, type:"union", aId:people[a], bId:people[b], unionType:o.type||"marriage", start:o.start||{mode:"unknown"}, startPlaceId:o.place?place(o.place):null, endReason:o.end||"", endDate:o.endDate||{mode:"unknown"}, status:o.status||"probable", citations:(o.cite||[]).map(c=>({sourceId:c[0], detail:c[1]||""})), created:stamp(), updated:T}; };

  // Generation 1
  person("tursun",{sex:"male", living:"deceased", names:[{given:"Tursun", surname:"Nurmatov"},{type:"arabic_script", full:"تورسون", script:"Arab"},{type:"cyrillic", given:"Турсун", surname:"Нурматов", script:"Cyrl"}], notes:"His father's name is not known. Family tradition says the family came to Namangan from the Kokand area, but no record has been found."});
  person("zulfiya",{sex:"female", living:"deceased", names:[{given:"Zulfiya", surname:"Nurmatova"},{type:"birth", given:"Zulfiya", surname:"Hamidova"},{type:"nickname", full:"Zulfi-opa"}]});
  // Generation 2
  person("karim",{sex:"male", living:"deceased", names:[{given:"Karim", patronymic:"Tursunovich", surname:"Nurmatov"},{type:"cyrillic", given:"Карим", patronymic:"Турсунович", surname:"Нурматов", script:"Cyrl"}], notes:"Birth year disagrees between the reissued certificate (1928) and his son's recollection (1927)."});
  person("malika",{sex:"female", living:"deceased", names:[{given:"Malika", surname:"Nurmatova"},{type:"birth", given:"Malika", surname:"Qodirova"}]});
  person("saodat",{sex:"female", living:"deceased", names:[{given:"Saodat", surname:"Sodiqova"},{type:"birth", given:"Saodat", surname:"Nurmatova"},{type:"married", given:"Saodat", surname:"Yusupova"}]});
  person("hamid",{sex:"male", living:"deceased", names:[{given:"Hamid", surname:"Nurmatov"}], notes:"Remembered only through family stories. Died in childhood; no record found yet."});
  person("bahodir",{sex:"male", living:"unknown", names:[{given:"Bahodir", surname:"Yusupov"}], notes:"First husband of Saodat. Contact with him was lost after the divorce."});
  person("olim",{sex:"male", living:"deceased", names:[{given:"Olim", surname:"Sodiqov"}]});
  // Generation 3
  person("rustam",{sex:"male", living:"living", names:[{given:"Rustam", patronymic:"Karimovich", surname:"Nurmatov"}]});
  person("gulnora",{sex:"female", living:"living", names:[{given:"Gulnora", surname:"Nurmatova"},{type:"birth", given:"Gulnora", surname:"Rahimova"}]});
  person("dilnoza",{sex:"female", living:"living", names:[{given:"Dilnoza", surname:"Aliyeva"},{type:"birth", given:"Dilnoza", surname:"Nurmatova"}]});
  person("sherzod",{sex:"male", living:"living", names:[{given:"Sherzod", surname:"Aliyev"}]});
  person("farrukh",{sex:"male", living:"living", names:[{given:"Farrukh", surname:"Nurmatov"},{type:"alternative", given:"Farruh", surname:"Nurmatov"}]});
  person("anvar",{sex:"male", living:"living", names:[{given:"Anvar", surname:"Yusupov"}]});
  person("nodira",{sex:"female", living:"living", names:[{given:"Nodira", surname:"Sodiqova"}]});
  // Generation 4
  person("timur",{sex:"male", living:"living", names:[{given:"Timur", surname:"Nurmatov"}]});
  person("aziza",{sex:"female", living:"living", names:[{given:"Aziza", surname:"Nurmatova"}]});
  person("laylo",{sex:"female", living:"living", names:[{given:"Laylo", surname:"Nurmatova"}], notes:"Adopted as an infant. Her biological parents are not recorded, and the family has chosen not to research them."});
  person("kamila",{sex:"female", living:"living", names:[{given:"Kamila", surname:"Aliyeva"}]});
  // Generation 5
  person("samir",{sex:"male", living:"living", names:[{given:"Samir", surname:"Nurmatov"}]});

  // Vital events
  ev("birth","tursun",{date:{mode:"about",y:1899}, place:"Namangan", status:"family_tradition", cite:[["ds4","p. 1"]]});
  ev("death","tursun",{date:{mode:"exact",y:1968,m:2,d:11}, place:"Tashkent", status:"probable", cite:[["ds4","p. 31"]]});
  ev("birth","zulfiya",{date:{mode:"before",y:1906}, status:"unverified"});
  ev("death","zulfiya",{date:{mode:"year",y:1975}, place:"Tashkent", status:"probable", cite:[["ds2","00:41:10"]]});
  ev("birth","karim",{date:{mode:"exact",y:1928,m:4,d:2}, place:"Namangan", status:"probable", cite:[["ds1","entry 214"]]});
  ev("birth","karim",{date:{mode:"year",y:1927}, place:"Namangan", status:"family_tradition", cite:[["ds2","00:05:30"]]});
  ev("death","karim",{date:{mode:"year",y:1999}, place:"Tashkent", status:"verified", cite:[["ds2","00:52:00"]]});
  ev("birth","malika",{date:{mode:"exact",y:1930,m:11,d:23}, place:"Tashkent", status:"verified", cite:[["ds3","age stated on certificate"]]});
  ev("death","malika",{date:{mode:"exact",y:2011,m:6,d:5}, place:"Tashkent", status:"verified"});
  ev("birth","saodat",{date:{mode:"about",y:1931}, place:"Namangan", status:"family_tradition", cite:[["ds4","p. 3"]]});
  ev("death","saodat",{date:{mode:"year",y:2003}, place:"Samarkand", status:"probable"});
  ev("birth","hamid",{date:{mode:"between",y:1934,y2:1936}, place:"Namangan", status:"family_tradition", cite:[["ds4","p. 3"]]});
  ev("death","hamid",{date:{mode:"about",y:1943}, status:"family_tradition", cite:[["ds4","p. 4"]]});
  ev("birth","bahodir",{date:{mode:"about",y:1927}, status:"unverified"});
  ev("birth","olim",{date:{mode:"year",y:1929}, place:"Samarkand", status:"probable"});
  ev("death","olim",{date:{mode:"year",y:1990}, place:"Samarkand", status:"probable"});
  ev("birth","rustam",{date:{mode:"exact",y:1953,m:7,d:30}, place:"Tashkent", status:"verified"});
  ev("birth","gulnora",{date:{mode:"year",y:1956}, place:"Andijan", status:"verified"});
  ev("birth","dilnoza",{date:{mode:"exact",y:1956,m:1,d:17}, place:"Tashkent", status:"verified"});
  ev("birth","sherzod",{date:{mode:"year",y:1954}, status:"unverified"});
  ev("birth","farrukh",{date:{mode:"year",y:1960}, place:"Tashkent", status:"verified"});
  ev("birth","anvar",{date:{mode:"year",y:1952}, place:"Namangan", status:"probable"});
  ev("birth","nodira",{date:{mode:"year",y:1963}, place:"Samarkand", status:"probable"});
  ev("birth","timur",{date:{mode:"exact",y:1980,m:5,d:12}, place:"Tashkent", status:"verified"});
  ev("birth","aziza",{date:{mode:"year",y:1984}, status:"verified"});
  ev("birth","laylo",{date:{mode:"year",y:1984}, status:"probable", cite:[["ds5",""]]});
  ev("birth","kamila",{date:{mode:"year",y:1982}, place:"Tashkent", status:"verified"});
  ev("birth","samir",{date:{mode:"year",y:2012}, place:"Tashkent", status:"verified"});
  // Life events
  ev("migration","karim",{date:{mode:"about",y:1950}, place:"Namangan", to:"Tashkent", title:"Moved to Tashkent for work", desc:"Family tradition says he left for Tashkent after finishing school. The year is remembered only as “around 1950”.", status:"family_tradition", cite:[["ds2","00:12:40"]]});
  ev("employment","karim",{date:{mode:"between",y:1953,y2:1988}, place:"Tashkent", title:"Schoolteacher (mathematics)", status:"probable", cite:[["ds2","00:15:00"]]});
  ev("education","rustam",{date:{mode:"between",y:1970,y2:1975}, place:"Tashkent", title:"Studied engineering", status:"unverified"});
  ev("migration","saodat",{date:{mode:"about",y:1961}, place:"Namangan", to:"Samarkand", with:["anvar"], title:"Moved to Samarkand after remarrying", status:"family_tradition"});

  // Relationships
  un("tursun","zulfiya",{type:"religious_marriage", start:{mode:"about",y:1925}, status:"family_tradition", cite:[["ds4","p. 1"]]});
  pc("tursun","karim",{status:"verified", cite:[["ds1",""]]}); pc("zulfiya","karim",{status:"verified", cite:[["ds1",""]]});
  pc("tursun","saodat",{status:"probable"}); pc("zulfiya","saodat",{status:"probable"});
  pc("tursun","hamid",{status:"family_tradition", cite:[["ds4","p. 3"]]}); pc("zulfiya","hamid",{status:"family_tradition", cite:[["ds4","p. 3"]]});
  un("karim","malika",{start:{mode:"exact",y:1952,m:9,d:14}, place:"Tashkent", status:"verified", end:"death", endDate:{mode:"year",y:1999}, cite:[["ds3","record 1187"]]});
  ["rustam","dilnoza","farrukh"].forEach(c=>{ pc("karim",c,{status:"verified"}); pc("malika",c,{status:"verified"}); });
  un("saodat","bahodir",{start:{mode:"about",y:1950}, place:"Namangan", end:"divorce", endDate:{mode:"about",y:1958}, status:"probable"});
  pc("saodat","anvar",{status:"verified"}); pc("bahodir","anvar",{status:"probable"});
  un("saodat","olim",{start:{mode:"year",y:1961}, place:"Samarkand", status:"probable", end:"death", endDate:{mode:"year",y:1990}});
  pc("saodat","nodira",{status:"verified"}); pc("olim","nodira",{status:"verified"});
  un("rustam","gulnora",{start:{mode:"year",y:1978}, place:"Tashkent", status:"verified"});
  pc("rustam","timur",{status:"verified"}); pc("gulnora","timur",{status:"verified"});
  pc("rustam","laylo",{nature:"adoptive", status:"verified", cite:[["ds5",""]]}); pc("gulnora","laylo",{nature:"adoptive", status:"verified", cite:[["ds5",""]]});
  un("dilnoza","sherzod",{start:{mode:"year",y:1980}, status:"verified"});
  pc("dilnoza","kamila",{status:"verified"}); pc("sherzod","kamila",{status:"verified"});
  un("timur","aziza",{start:{mode:"year",y:2009}, place:"Tashkent", status:"verified"});
  pc("timur","samir",{status:"verified"}); pc("aziza","samir",{status:"verified"});

  A.branches["db1"] = {id:"db1", name:"Nurmatov line", founderId:people.tursun, description:"Descendants of Tursun Nurmatov.", created:stamp(), updated:T};
  A.branches["db2"] = {id:"db2", name:"Yusupov line", founderId:people.bahodir, description:"Descendants of Bahodir Yusupov.", created:stamp(), updated:T};
  A.meta["archive"] = {id:"archive", title:"The Nurmatov family (demo)", created:T, updated:T};
  return {A: localizeDemo(A), root: people.rustam};
}
