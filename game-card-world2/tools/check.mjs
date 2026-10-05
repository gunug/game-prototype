// 기본 오류 검사 — 브라우저 없이 index.html 스크립트를 확인
//   1) 문법 검사 (node --check 와 같음)
//   2) 가짜 DOM에서 시작 코드 실행 → 선언 순서(TDZ)·없는 변수 같은 시작 오류
//   3) 등록된 타이머·rAF 콜백을 한 번씩 실행 → 그 안의 오류
// 사용: node tools/check.mjs  (게임 폴더에서)
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const dir = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(dir, 'index.html'), 'utf8');
const scripts = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]);
let fail = 0;
const report = (step, e) => { fail++; console.log(`✗ ${step}: ${e && e.stack ? e.stack.split('\n').slice(0, 3).join('\n  ') : e}`); };

// 1) 문법
const code = scripts.join('\n;\n');
try { new vm.Script(code, { filename: 'index.html<script>' }); console.log(`✓ 문법 (스크립트 ${scripts.length}개)`); }
catch (e){ report('문법', e); process.exit(1); }

// 2) 가짜 DOM: 무엇을 읽든 호출하든 또 가짜를 돌려줌. 숫자·문자로 쓰면 0/''
function fake(name = 'fake'){
  const store = {};
  return new Proxy(function(){}, {
    get(_, k){
      if (k === Symbol.toPrimitive) return hint => hint === 'string' ? '' : 0;
      if (k === 'then') return undefined;
      if (k === Symbol.iterator) return function*(){};
      if (k in store) return store[k];
      if (k === 'length') return 0;
      return (store[k] = fake(`${name}.${String(k)}`));
    },
    set(_, k, v){ store[k] = v; return true; },
    apply(){ return fake(`${name}()`); },
    construct(){ return fake(`new ${name}`); },
  });
}
const timers = [];
const mem = new Map();
const doc = fake('document');
const ctx = {
  console, Math, JSON, Date, Map, Set, Promise, Object, Array, String, Number, Symbol, Error, RegExp, parseInt, parseFloat, isNaN,
  document: doc,
  localStorage: { getItem: k => mem.has(k) ? mem.get(k) : null, setItem: (k, v) => mem.set(k, String(v)), removeItem: k => mem.delete(k) },
  performance: { now: () => Date.now() },
  innerWidth: 1280, innerHeight: 800, devicePixelRatio: 1,
  setTimeout: (f) => { timers.push(f); return timers.length; }, clearTimeout(){},
  setInterval: (f) => { timers.push(f); return timers.length; }, clearInterval(){},
  requestAnimationFrame: (f) => { timers.push(f); return timers.length; }, cancelAnimationFrame(){},
  addEventListener(){}, removeEventListener(){}, confirm: () => false, alert(){},
  getComputedStyle: () => fake('style'), matchMedia: () => fake('mql'),
};
ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
try { vm.runInContext(code, ctx, { filename: 'index.html<script>' }); console.log('✓ 시작 실행'); }
catch (e){ report('시작 실행', e); }

// 3) 타이머 콜백 한 번씩 (새로 등록되는 건 안 돌림)
const once = timers.splice(0);
for (const f of once){
  try { const r = f(16); if (r && typeof r.catch === 'function') r.catch(e => report('타이머(async)', e)); }
  catch (e){ report('타이머', e); }
}
console.log(`✓ 타이머·rAF 콜백 ${once.length}개 실행`);

// 4) 저장 → **새로 고침** (v0.76.0) — 여러 모양의 저장으로 각각 확인
//   시작 코드에서 load()가 조용히 실패하면(아직 선언 전인 전역을 건드리는 TDZ 등 → catch가 삼킴)
//   진행이 통째로 버려진다. 첫 실행 때만 나는 오류라 '스크립트를 처음부터 다시 돌리는' 방식으로만 잡힌다
function refresh(label, setup, expect){
  try {
    if (setup) vm.runInContext(setup, ctx);
    const ctx2 = { ...ctx };                                      // 같은 localStorage(mem)를 쓰는 새 판
    ctx2.document = fake('document');
    ctx2.setTimeout = () => 0; ctx2.setInterval = () => 0; ctx2.requestAnimationFrame = () => 0;
    ctx2.window = ctx2; ctx2.globalThis = ctx2; ctx2.self = ctx2;
    vm.createContext(ctx2);
    vm.runInContext(code, ctx2, { filename: `index.html<script> (새로 고침: ${label})` });
    const got = JSON.parse(vm.runInContext(
      'JSON.stringify({ lv: S.knight.lv, xp: S.knight.xp, seen: S.seen.length, tab: S.tab, cards: S.cards.length })', ctx2));
    for (const k in expect){
      if (got[k] !== expect[k]){ report(`새로 고침(${label})`, new Error(`${k} = ${got[k]}, ${expect[k]} 이어야 함 — 저장이 버려졌을 수 있음: ${JSON.stringify(got)}`)); return; }
    }
    console.log(`✓ 저장 → 새로 고침 (${label})`);
  } catch (e){ report(`새로 고침(${label})`, e); }
}
refresh('보통', "S.seen = ['stone','flint']; S.knight.lv = 6; S.knight.xp = 7; S.killed = ['wolf']; S.cards = [{id:1,type:'stone',x:0,y:0,n:3}]; save();",
  { lv: 6, xp: 7, seen: 2, cards: 1 });
refresh('예전 저장', `localStorage.setItem(SAVE_KEY, JSON.stringify({
  cards: [{ id:1, type:'stone', x:0, y:0 }, { id:2, type:'stone', x:0, y:0 }, { id:3, type:'없는카드', x:0, y:0 }],
  seen: ['stone','없는카드'], tab: 'gather', quest: { id:'gomountain', n:0 },
  fields: { mountain:{ locked:false, left:3 } }, lootSeen: { animal:['meat'] } }));`,
  { lv: 1, xp: 0, seen: 1, tab: 'battle', cards: 1 });             // 같은 카드는 한 장으로 합쳐짐
refresh('에디터 모드', "S.seen = ['stone']; S.knight.lv = 3; save(); localStorage.setItem(EDIT_KEY, '1');",
  { lv: 3 });
vm.runInContext("localStorage.removeItem(EDIT_KEY);", ctx);

// 5) 같은 두 장이 탭마다 다른 결과를 내지 않는지 (v1.4.0) — 사용자가 헷갈림
try {
  const clash = vm.runInContext(`(function(){
    const out = [], nm = t => DEFS[t].name, boards = BOARDS.filter(b => b.dyn || b.mats).map(b => b.id);   // v6.4.0: 재료 탭도 함께 본다
    const here = (t, b) => onBoard(t, b) || onTopGrid(t, b);
    for (let i = 0; i < CRAFT_TYPES.length; i++) for (let j = i + 1; j < CRAFT_TYPES.length; j++){
      const x = CRAFT_TYPES[i], y = CRAFT_TYPES[j], res = {};
      for (const b of boards){
        if (!here(x, b) || !here(y, b)) continue;
        const m = usableRecipes(x, y).find(mm => CRAFT_RECIPES.includes(mm.r) && boardMakes(mm.r, b));
        if (m) res[b] = (m.r.out || []).join('/');
      }
      if (new Set(Object.values(res)).size > 1) out.push(nm(x) + ' + ' + nm(y) + ' → ' + JSON.stringify(res));
    }
    return out;
  })()`, ctx);
  if (clash.length) report('탭마다 다른 결과', new Error(clash.join(' / ')));
  else console.log('✓ 같은 두 장은 어느 탭에서나 같은 결과');
} catch (e){ report('탭마다 다른 결과', e); }

// 6) 화면 조각을 실제로 그려 본다 (v3.4.0) — 지우다 만 함수처럼 '그릴 때만 터지는' 오류를 잡음
try {
  vm.runInContext(`(function(){
    S.seen = CRAFT_TYPES.slice(0, 8); S.cards = [{ id:1, type:CRAFT_TYPES[0], n:2, x:0, y:0 }];
    bookOpen = true;
    for (const t of BOOK_BOARDS().map(b => b.id).concat([COMBO_TAB, TRACE_TAB, TREE_TAB])){ bookTier = t; renderBook(); }
    bookTier = TREE_TAB;
    for (const id in TREES){ bookTree = id; renderBook(); }
    S.goal = CRAFT_TYPES.find(t => CRAFT_RECIPES.some(r => (r.out || []).includes(t))) || null;
    goalRowHtml(); goalPlanHtml(); opNote(); renderQuest();
    for (const tab of ['aim', 'battle', 'gearup', 'inn']){ S.tab = tab; screenRows(); screenTokens(); }
    // v9.55.0: 여관 — 등록 전 · 세 걸음 각각 · 정보 칸(장인 다섯 + 여관 주인)
    S.tab = 'inn';
    S.inn = { reg:'armorsmith', prog:{}, given:{}, done:['weaponsmith'], found:['weaponsmith'] };
    for (const n of [0, 1, 2]){ S.inn.prog.armorsmith = n; screenRows(); screenTokens(); }
    for (const id of SMITHS.map(x => x.id).concat('keeper')){ innPick = id; renderInsp(); }
    innPick = null; S.inn = freshInn();
    S.tab = 'aim'; aimCandidates();
    for (const t of CRAFT_TYPES.slice(0, 12)){ inspType = t; S.tab = 'tool'; renderInsp(); }
    // v4.7.0: 좁은 화면 ☰ 메뉴 — 접고 펴고 다시 넓혀도 단추가 살아 있는지
    for (const nw of [true, false, true, false]){ narrowUI = nw; setNavOpen(nw); renderTabs(); tabName(S.tab); }
    narrowUI = false; setNavOpen(false);   // 가짜 DOM이라 개수는 못 셈 — 접고 펴며 터지는지만 본다
    // v7.0.0: 모든 조합식은 **어딘가에서 만들 수 있어야** 한다 (재료 둘이 한 탭에 같이 있고 그 탭이 그 조합을 맡음)
    const noHome = CRAFT_RECIPES.filter(r => !BOARDS.some(b => sideOnBoard(r.a, b.id) && sideOnBoard(r.b, b.id) && boardMakes(r, b.id)))
      .map(r => r.id);
    if (noHome.length) throw new Error('만들 탭이 없는 조합식: ' + noHome.join(', '));
    // 모든 카드는 어느 탭엔가 실려야 한다 (갈래 태그가 없으면 어디에도 안 보인다)
    const lost = CRAFT_TYPES.filter(t => !BOARDS.some(b => onBoard(t, b.id) || onTopGrid(t, b.id))).map(t => DEFS[t].name);
    if (lost.length) throw new Error('어느 탭에도 없는 카드: ' + lost.join(', '));
    // v4.6.0: 조합 탭마다 위 격자 · 아래 재료가 비지 않는지
    const empty = [];
    for (const b of BOARDS){
      if (!b.tops) continue;                                       // v4.8.0: 조합 탭은 한 판 — 위 격자가 없다
      if (!CRAFT_TYPES.some(t => onBoard(t, b.id) || onTopGrid(t, b.id))) continue;   // v7.0.0: 통째로 빈 탭은 단추가 숨는다
      S.tab = b.id; renderTopGrid(); renderTabs();
      const top = CRAFT_TYPES.filter(t => onTopGrid(t, b.id)), bot = CRAFT_TYPES.filter(t => onBoard(t, b.id));
      if (!top.length || !bot.length) empty.push(b.name + '(위 ' + top.length + ' · 아래 ' + bot.length + ')');
    }
    if (empty.length) throw new Error('빈 조합 탭: ' + empty.join(' / '));
    return 1;
  })()`, ctx);
  console.log('✓ 화면 조각 렌더 (콜렉터북 · 트리 · 수첩 · 목적 · 인스펙터)');
} catch (e){ report('화면 렌더', e); }

// 6.5) v7.3.0: 카드 이름 길이 — 다섯 글자 + 띄어쓰기 하나가 한계 (카드가 좁아 두 줄로 접힘)
try {
  const long = vm.runInContext(`(function(){
    const over = n => n.replace(/ /g, '').length > 5 || (n.match(/ /g) || []).length > 1;
    const bad = CRAFT_TYPES.filter(t => over(DEFS[t].name)).map(t => DEFS[t].name);
    for (const k in ENEMIES) if (over(ENEMIES[k].name)) bad.push(ENEMIES[k].name);   // v7.9.2: 크리처도 같은 규칙
    for (const f of FIELDS) if (over(f.name)) bad.push(f.name);                      // 땅 이름도
    return JSON.stringify(bad);
  })()`, ctx);
  const list = JSON.parse(long);
  if (list.length) report('카드 이름 길이', new Error('너무 긴 이름: ' + list.join(', ')));
  else console.log('✓ 카드 이름 (다섯 글자 + 띄어쓰기 하나 안쪽)');
} catch (e){ report('카드 이름 길이', e); }

// 6.6) v7.4.0: 콜렉터북 — 카드는 **정확히 한 자리**에 실려야 한다 (재료는 나오는 곳 또는 만드는 곳)
try {
  const stray = JSON.parse(vm.runInContext(`JSON.stringify(CRAFT_TYPES.filter(t => !isFinished(t))
    .filter(t => !FIELDS.some(f => yieldsOf(f.id).includes(t) || lootTypes(f.id).includes(t)) && !recipeTabOf(t))
    .map(t => DEFS[t].name))`, ctx));
  const both = JSON.parse(vm.runInContext(`JSON.stringify(CRAFT_TYPES.filter(t => bookCardsOf('mat').includes(t) && bookCardsOf('fin').includes(t)).map(t => DEFS[t].name))`, ctx));
  if (stray.length) report('콜렉터북 자리', new Error('묶일 곳이 없는 재료: ' + stray.join(', ')));
  else if (both.length) report('콜렉터북 자리', new Error('재료와 완성품 양쪽에 실린 카드: ' + both.join(', ')));
  else console.log('✓ 콜렉터북 자리 (카드마다 한 자리)');
} catch (e){ report('콜렉터북 자리', e); }

// 7) 같은 두 재료가 서로 다른 결과를 내는 조합식이 있는지 (v3.7.1) — 어느 쪽이 만들어질지 모르게 된다
try {
  const dup = vm.runInContext(`(function(){
    const seen = {}, out = [];
    for (const r of CRAFT_RECIPES){
      if (r.cook || !r.a.card || !r.b.card) continue;
      const key = [r.a.card, r.b.card].sort().join('+');
      const res = (r.out || []).join('/');
      if (seen[key] && seen[key] !== res) out.push(key + ' -> ' + seen[key] + ' / ' + res);
      else seen[key] = res;
    }
    return out;
  })()`, ctx);
  if (dup.length) report('같은 재료 · 다른 결과', new Error(dup.join(' | ')));
  else console.log('✓ 같은 두 재료는 결과가 하나뿐');
} catch (e){ report('같은 재료 · 다른 결과', e); }

// 8) 단계 규칙 (v3.11.0) — N단계는 (N−1)+(N−1) 또는 (N−1)+(N−2) 로만 만든다
try {
  const bad = vm.runInContext(`(function(){
    const out = [], nm = t => (DEFS[t] ? DEFS[t].name : t);
    for (const r of CRAFT_RECIPES){
      if (r.cook || !r.a.card || !r.b.card) continue;
      const sa = DEFS[r.a.card].step || 0, sb = DEFS[r.b.card].step || 0;
      for (const o of (r.out || [])){
        const so = DEFS[o].step || 0, hi = Math.max(sa, sb), lo = Math.min(sa, sb);
        if (so !== hi + 1 || hi - lo > 1)
          out.push(nm(o) + '(' + so + ') <- ' + nm(r.a.card) + '(' + sa + ') + ' + nm(r.b.card) + '(' + sb + ')');
      }
    }
    return out;
  })()`, ctx);
  if (bad.length) report('단계 규칙', new Error(bad.join(' | ')));
  else console.log('✓ 단계 규칙 (N = 아래 단계 + 1, 두 재료의 단계 차는 1 이하)');
} catch (e){ report('단계 규칙', e); }

// 9) 무기끼리는 안 합친다 (v9.28.2) — 완성된 무기는 상단 필드로 올라가 서로 만날 수 없다.
//    무기는 늘 **무기 + 무기재료** 꼴이어야 한다
try {
  const bad = vm.runInContext(`(function(){
    const out = [], nm = t => (DEFS[t] ? DEFS[t].name : t);
    const isW = t => useOf(t).includes('무기');
    for (const r of CRAFT_RECIPES){
      if (r.cook || !r.a.card || !r.b.card) continue;
      if (isW(r.a.card) && isW(r.b.card))
        out.push(nm(r.a.card) + ' + ' + nm(r.b.card) + ' -> ' + (r.out || []).map(nm).join(','));
    }
    return out;
  })()`, ctx);
  if (bad.length) report('무기끼리 합침', new Error(bad.join(' | ')));
  else console.log('✓ 무기끼리 합치는 조합식 0 (무기 + 무기재료만)');
} catch (e){ report('무기끼리 합침', e); }

// 10) 진행 막힘 없음 (v9.54.0) — 던전의 기믹을 깰 무기는 **그 던전에 닿기 전에 열리는 땅들만으로** 만들 수 있어야 한다.
//     조합식을 손볼 때(새 재료를 끼울 때) 그 무기의 재료가 뒷땅으로 밀려나면 그 지점에서 영원히 막힌다
try {
  const r = vm.runInContext(`(function(){
    // 몇 번째 물결에 열리는 땅인가 (열 조건이 없으면 0)
    const waveOf = id => { let w = 0, cur = id, seen = {};
      while (true){ const p = unlockAfter(cur); if (!p || seen[p]) break; seen[p] = 1; w++; cur = p; } return w; };
    // 그 땅에서 **얻을 수 있는** 1단계 — 줍는 것 + 사는 것들이 떨구는 것
    const fromField = id => { const out = new Set(yieldsOf(id));
      for (const st of (planOf(id) || [])) for (const l of ((ENEMIES[st.fight] || {}).loot || [])) out.add(l[0]);
      return [...out]; };
    // 물결 w 까지 열린 땅으로 만들 수 있는 모든 것 (조합식 닫힘)
    const upto = w => { const have = new Set();
      for (const f of FIELDS) if (waveOf(f.id) <= w) for (const t of fromField(f.id)) have.add(t);
      for (let i = 0; i < 12; i++) for (const rc of CRAFT_RECIPES){
        if (rc.cook || !rc.a.card || !rc.b.card) continue;
        if (have.has(rc.a.card) && have.has(rc.b.card)) for (const o of (rc.out || [])) have.add(o);
      }
      return have; };
    const isW = t => useOf(t).includes('무기');
    const ANSWER = { swamptomb: ['bleed', '출혈'], spidernest: ['range', '원거리'], shellcave: ['multi', '연타'] };
    const bad = [], far = [];
    for (const id in ANSWER){
      const [prop, say] = ANSWER[id], w = waveOf(id);
      const have = upto(w - 1);                                   // **그 땅에 들어가기 전**까지
      const ok = [...have].some(t => isW(t) && (DEFS[t][prop] || 0) >= (prop === 'range' ? 2 : 1));
      if (!ok) bad.push(FIELD_BY_ID[id].name + ' — ' + say + ' 무기를 먼저 만들 수 없다');
    }
    const last = upto(99);                                        // 끝까지 열어도 못 만드는 조합식
    for (const rc of CRAFT_RECIPES){
      if (rc.cook || !rc.a.card || !rc.b.card) continue;
      if (!last.has(rc.a.card) || !last.has(rc.b.card)) far.push((rc.id || '?') + ': ' + (DEFS[rc.a.card]||{}).name + ' + ' + (DEFS[rc.b.card]||{}).name);
    }
    return { bad, far };
  })()`, ctx);
  const msg = r.bad.concat(r.far.length ? ['닿을 수 없는 조합식 ' + r.far.length + '개 — ' + r.far.slice(0, 4).join(' | ')] : []);
  if (msg.length) report('진행 막힘', new Error(msg.join(' | ')));
  else console.log('✓ 진행 막힘 없음 (기믹 해법 무기는 그 땅 전에 만들 수 있고, 모든 조합식이 닿는다)');
} catch (e){ report('진행 막힘', e); }

// 11) 장인 걸음이 닿는가 (v9.55.0) — 여관의 세 걸음(소문 · 물건 · 증명)이 **그 장인을 찾을 수 있는 시점에**
//     전부 가능해야 한다. 재료를 뒷땅에서만 구하거나, 지목한 놈이 그 땅에 없으면 그 자리에서 영원히 막힌다
try {
  const bad = vm.runInContext(`(function(){
    const out = [];
    const waveOf = id => { let w = 0, cur = id, seen = {};
      while (true){ const p = unlockAfter(cur); if (!p || seen[p]) break; seen[p] = 1; w++; cur = p; } return w; };
    const fromField = id => { const got = new Set(yieldsOf(id));
      for (const st of (planOf(id) || [])) for (const l of ((ENEMIES[st.fight] || {}).loot || [])) got.add(l[0]);
      return [...got]; };
    const upto = w => { const have = new Set();
      for (const f of FIELDS) if (waveOf(f.id) <= w) for (const t of fromField(f.id)) have.add(t);
      for (let i = 0; i < 12; i++) for (const rc of CRAFT_RECIPES){
        if (rc.cook || !rc.a.card || !rc.b.card) continue;
        if (have.has(rc.a.card) && have.has(rc.b.card)) for (const o of (rc.out || [])) have.add(o);
      }
      return have; };
    for (const sm of SMITHS){
      if (sm.free){                                               // 처음부터 있는 사람은 걸음이 없다
        if (sm.land || sm.give || sm.proof) out.push(sm.name + ' — 처음부터 있는데 걸음이 붙어 있다');
        continue;
      }
      if (!FIELD_BY_ID[sm.land]) { out.push(sm.name + ' — 소문의 땅이 없다'); continue; }
      if (!ENEMIES[sm.proof]) { out.push(sm.name + ' — 증명할 놈이 없다'); continue; }
      const w = waveOf(sm.land);
      const here = (planOf(sm.land) || []).some(st => st.fight === sm.proof);
      if (!here) out.push(sm.name + ' — ' + ENEMIES[sm.proof].name + '이 ' + FIELD_BY_ID[sm.land].name + '에 없다');
      const have = upto(w);                                       // 그 땅이 열린 시점까지
      for (const [t, n] of (sm.give || [])){
        if (!DEFS[t]) { out.push(sm.name + ' — 없는 재료 ' + t); continue; }
        if (!have.has(t)) out.push(sm.name + ' — ' + DEFS[t].name + ' ' + n + '을 그때 구할 수 없다');
        // v9.56.4: 내는 물건은 **줍거나 떨구는 날것**이어야 한다 — 만들어야 하는 것이면 그 탭이 잠겨 막힐 수 있다
        if ((DEFS[t].step || 0) > 1) out.push(sm.name + ' — ' + DEFS[t].name + '은 만들어야 하는 것이다 (1단계만)');
      }
      const o = sm.opens || {};
      if (o.board && !BOARD_BY_ID[o.board]) out.push(sm.name + ' — 없는 탭 ' + o.board);
      if (o.slot && !slotByKey(o.slot)) out.push(sm.name + ' — 없는 칸 ' + o.slot);
    }
    // 칸과 탭마다 **맡은 장인이 하나**여야 한다 (아무도 안 맡으면 영원히 잠긴다)
    for (const sl of SLOTS) if (sl.smith && !SMITH_BY_ID[sl.smith]) out.push(sl.name + ' 칸 — 없는 장인 ' + sl.smith);
    for (const b of BOARDS) if (b.smith && !SMITH_BY_ID[b.smith]) out.push(b.name + ' 탭 — 없는 장인 ' + b.smith);
    return out;
  })()`, ctx);
  if (bad.length) report('장인 걸음', new Error(bad.join(' | ')));
  else console.log('✓ 장인 걸음이 닿는다 (소문의 땅 · 물건 재료 · 증명할 놈이 그 시점에 다 있다)');
} catch (e){ report('장인 걸음', e); }

setTimeout(() => { console.log(fail ? `\n오류 ${fail}개` : '\n오류 없음'); process.exit(fail ? 1 : 0); }, 50);
