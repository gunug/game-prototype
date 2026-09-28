// AI 테스트 모드 (v7.14.0) — 화면 없이, 연출 없이, **규칙과 확률은 그대로** 게임을 끝까지 돌려 본다.
//   · 시계를 가짜로 돌려 원정 45초는 45초로 기록되지만 실제로는 눈 깜짝할 새에 끝난다
//   · 조작은 드래그가 아니라 게임 함수를 그대로 부른다 (craft · expStart · equipCard …) — 확률 계산도 그대로
//   · 끝나면 플레이 기록(설정의 '진행도 + 기록' 과 같은 것)과 요약을 찍는다
//
// 사용:
//   node tools/sim.mjs                 한 판
//   node tools/sim.mjs --runs 20       스무 판 돌려 평균
//   node tools/sim.mjs --seed 7        같은 난수로 재현
//   node tools/sim.mjs --json out.json 기록을 파일로
//   node tools/sim.mjs --log           걸음을 한 줄씩 보며
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const HTML = fs.readFileSync(path.join(DIR, 'index.html'), 'utf8');
const CODE = [...HTML.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

const argv = process.argv.slice(2);
const arg = (k, d) => { const i = argv.indexOf(k); return i < 0 ? d : argv[i + 1]; };
const has = k => argv.includes(k);
const RUNS = +arg('--runs', 1);
const SEED0 = arg('--seed', null);
const VERBOSE = has('--log');
const MAX_MIN = +arg('--max-min', 240);              // 게임 속 시간 한계 (분)

// ── 가짜 DOM — check.mjs 와 같은 얼개 (무엇을 읽든 또 가짜를 돌려줌)
function fake(){
  const store = {};
  return new Proxy(function(){}, {
    get(_, k){
      if (k === Symbol.toPrimitive) return hint => hint === 'string' ? '' : 0;
      if (k === 'then') return undefined;
      if (k === Symbol.iterator) return function*(){};
      if (k in store) return store[k];
      if (k === 'length') return 0;
      return (store[k] = fake());
    },
    set(_, k, v){ store[k] = v; return true; },
    apply(){ return fake(); },
    construct(){ return fake(); },
  });
}

// ── 시드 난수 (mulberry32) — 시드를 주면 같은 판이 재현된다
function rngOf(seed){
  let a = seed >>> 0;
  return () => { a |= 0; a = a + 0x6D2B79F5 | 0;
    let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
    return ((t ^ t >>> 14) >>> 0) / 4294967296; };
}

function boot(seed){
  // 가상 시계 · 타이머 줄 — 실제로 기다리지 않고 '그만큼 흐른 셈' 친다
  let now = Date.UTC(2026, 0, 1, 9, 0, 0);
  const timers = [];
  let tid = 1;
  const clock = {
    now: () => now,
    advance(ms){                                                   // ms 만큼 흘려 보내며 걸린 타이머를 차례로 실행
      const end = now + ms;
      for (let guard = 0; guard < 100000; guard++){
        const due = timers.filter(t => t.at <= end).sort((a, b) => a.at - b.at)[0];
        if (!due) break;
        now = Math.max(now, due.at);
        if (due.every) due.at = now + due.ms; else timers.splice(timers.indexOf(due), 1);
        try { due.fn(); } catch (e){ if (VERBOSE) console.log('  (타이머 오류)', String(e).slice(0, 80)); }
      }
      now = end;
    },
  };
  class SimDate extends Date {
    constructor(...a){ super(...(a.length ? a : [now])); }
    static now(){ return now; }
  }
  const mem = new Map();
  const rand = seed == null ? Math.random : rngOf(seed);
  const ctx = {
    console: VERBOSE ? console : { log(){}, warn(){}, error(){} },
    Math: Object.assign(Object.create(Math), { random: rand }),
    JSON, Date: SimDate, Map, Set, Promise, Object, Array, String, Number, Symbol, Error, RegExp,
    parseInt, parseFloat, isNaN, document: fake(),
    localStorage: { getItem: k => mem.has(k) ? mem.get(k) : null, setItem: (k, v) => mem.set(k, String(v)), removeItem: k => mem.delete(k) },
    performance: { now: () => now },
    innerWidth: 1280, innerHeight: 800, devicePixelRatio: 1,
    setTimeout: (fn, ms = 0) => { const id = tid++; timers.push({ id, at: now + ms, fn }); return id; },
    clearTimeout: id => { const i = timers.findIndex(t => t.id === id); if (i >= 0) timers.splice(i, 1); },
    setInterval: (fn, ms = 0) => { const id = tid++; timers.push({ id, at: now + ms, fn, every: true, ms }); return id; },
    clearInterval: id => { const i = timers.findIndex(t => t.id === id); if (i >= 0) timers.splice(i, 1); },
    requestAnimationFrame: () => 0, cancelAnimationFrame(){},       // 카드 밀어내기는 그림이라 돌릴 까닭이 없다
    addEventListener(){}, removeEventListener(){}, confirm: () => false, alert(){},
    getComputedStyle: () => fake(), matchMedia: () => fake(),
  };
  ctx.window = ctx; ctx.globalThis = ctx; ctx.self = ctx;
  vm.createContext(ctx);
  vm.runInContext(CODE, ctx, { filename: 'index.html<script>' });
  ctx.document.hidden = false;                                     // 화면을 보고 있는 셈 (논 시간이 흐르게)
  vm.runInContext('FAST = true', ctx);                             // 연출 건너뛰기 (규칙 · 확률은 그대로)
  return { ctx, clock };
}

// ── 게임에게 시키는 손짓 (사람이 드래그로 하던 것과 같은 함수를 부른다)
function makeAI({ ctx, clock }){
  const g = expr => vm.runInContext(expr, ctx);
  const call = (fn, ...args) => { ctx.__args = args; return vm.runInContext(`${fn}(...__args)`, ctx); };
  const ai = {
    ctx, clock,
    get S(){ return ctx.S; },
    advance: ms => clock.advance(ms),
    touch(){ vm.runInContext('lastInput = Date.now()', ctx); },    // 방치로 치지 않게 (사람이 조작한 셈)
    state(){
      return g(`(function(){
        const cards = {}; for (const c of S.cards) if (c.n > 0) cards[c.type] = (cards[c.type] || 0) + c.n;
        return JSON.parse(JSON.stringify({
          lv: S.knight.lv, hp: S.knight.hp, maxhp: knightMaxHp(), atk: knightAtk(), def: knightDef(),
          exp: !!exp, tab: S.tab, goal: S.goal, cards, seen: S.seen.length,
          equip: S.equip, cleared: S.cleared || [],
          fields: FIELDS.filter(f => !fieldLocked(f.id)).map(f => f.id),
          quests: (S.quests || []).filter(q => !q.done).map(q => q.id),
        }));
      })()`);
    },
    // 재료 둘을 합친다 — 손으로 끌어다 놓는 것과 같은 길
    craft(a, b){
      // 사람이 하듯 **그 조합을 할 수 있는 탭으로 먼저 옮긴 뒤** 합친다
      return g(`(function(){
        const A = ${JSON.stringify(a)}, B = ${JSON.stringify(b)};
        const ca = S.cards.find(c => c.type === A && c.n > 0);
        const cb = S.cards.find(c => c.type === B && c.n > 0);
        if (!ca || !cb || ca === cb) return false;
        const r0 = CRAFT_RECIPES.find(r => !r.cook
          && ((sideMatch(r.a, A) && sideMatch(r.b, B)) || (sideMatch(r.a, B) && sideMatch(r.b, A))));
        if (!r0) return false;
        const boards = recipeBoards(r0);
        if (!boards.length) return false;
        if (!boards.includes(S.tab)) setTab(boards[0]);
        const m = craftMatch(ca.type, cb.type);
        if (!m) return false;
        return craft(ca, cb, m) !== false;
      })()`);
    },
    canCraft(a, b){ return g(`!!craftMatch(${JSON.stringify(a)}, ${JSON.stringify(b)})`); },
    goal(t){ return call('setGoal', t); },
    plan(t){ return g(`JSON.parse(JSON.stringify(goalSteps(${JSON.stringify(t)})))`); },
    // 아직 안 끝난 걸음들 (게임의 판정을 그대로 쓴다)
    todo(t){ return g(`JSON.parse(JSON.stringify(goalSteps(${JSON.stringify(t)}).filter(st => !planStepDone(st))))`); },
    candidates(){ return g(`JSON.parse(JSON.stringify(aimCandidates()))`); },
    equip(slot, type){ return g(`(function(){ const sl = slotByKey(${JSON.stringify(slot)}); if (!sl || !slotOpen(sl.key)) return false;
      if (!(have(${JSON.stringify(type)}) > 0)) return false; equipCard(sl, ${JSON.stringify(type)}); return true; })()`); },
    tab(id){ return call('setTab', id); },
    sortie(field){
      const before = g('!!exp');
      if (before) return 'busy';
      call('expStart', field, ctx.document.createElement('div'));   // flash() 가 만질 가짜 카드
      return g('!!exp') ? 'go' : 'blocked';
    },
    // 원정이 끝날 때까지 시간을 흘려 보낸다 (최대 5분치)
    finishExp(){
      for (let i = 0; i < 600 && g('!!exp'); i++) clock.advance(500);
      clock.advance(3000);                                         // 끝맺음 타이머(귀환 · 대사)
      return !g('!!exp');
    },
    restTo(frac = 1){                                              // 체력이 그만큼 찰 때까지 쉰다
      for (let i = 0; i < 600; i++){
        if (g('S.knight.hp') >= Math.floor(g('knightMaxHp()') * frac)) return true;
        clock.advance(1000);
      }
      return false;
    },
    yieldsOf(id){ return g(`JSON.parse(JSON.stringify(yieldsOf(${JSON.stringify(id)})))`); },
    lootOf(id){ return g(`JSON.parse(JSON.stringify(lootTypes(${JSON.stringify(id)})))`); },
    fields(){ return g(`JSON.parse(JSON.stringify(FIELDS.map(f => ({ id: f.id, name: f.name, dungeon: !!f.dungeon, locked: fieldLocked(f.id) }))))`); },
    log(){ return g('JSON.parse(JSON.stringify(LOG))'); },
    snapshot(){ return g('JSON.parse(JSON.stringify(progressSnapshot()))'); },
    minutes(){ return (clock.now() - g('LOG.start')) / 60000; },
  };
  return ai;
}

// ── 정책 — '그럭저럭 사람처럼' 두는 수
//   ① 쥘 수 있는 가장 센 무기 · 방어구를 쥔다
//   ② 목표가 없으면 만들 수 있는 것 중 가장 센 장비를 목표로 건다
//   ③ 목표 차례대로: 만들 수 있으면 만들고, 재료가 모자라면 그게 나오는 땅으로 원정
//   ④ 다 갖췄으면 아직 못 깬 땅으로 원정 (약하면 쉰다)
function play(ai, note){
  const g = expr => vm.runInContext(expr, ai.ctx);
  const best = (use) => g(`(function(){
    let bestT = null, bestV = -1;
    for (const t of CRAFT_TYPES){
      if (!useOf(t).includes(${JSON.stringify(use)}) || have(t) <= 0) continue;
      const v = (DEFS[t].atk || 0) * 2 + (DEFS[t].def || 0) * 2 + (DEFS[t].pierce ? 3 : 0) + (DEFS[t].bleed || 0);
      if (v > bestV){ bestV = v; bestT = t; }
    }
    return bestT;
  })()`);
  const equipBest = () => {
    for (const [slot, use] of [['weapon', '근접무기'], ['armor', '방어구'], ['shield', '방패'], ['trinket', '장신구'], ['camp', '거점']]){
      const t = best(use);
      if (t && g(`equipped(${JSON.stringify(slot)})`) !== t) ai.equip(slot, t);
    }
  };
  const fieldFor = type => {                                      // 그 재료가 나오는, 지금 갈 수 있는 땅
    for (const f of ai.fields()){
      if (f.locked) continue;
      if (ai.yieldsOf(f.id).includes(type) || ai.lootOf(f.id).includes(type)) return f.id;
    }
    return null;
  };
  let stuck = 0, lastSig = '';
  const downs = {};                                               // 땅마다 진 횟수
  for (let step = 0; step < 4000; step++){
    if (ai.minutes() > MAX_MIN) return '시간 한계';
    const st = ai.state();
    const sig = `${st.lv}|${st.cleared.length}|${st.seen}|${Object.keys(st.cards).length}|${st.goal}`;
    stuck = sig === lastSig ? stuck + 1 : 0;
    lastSig = sig;
    if (stuck > 120){
      if (VERBOSE) console.log('   막힘 상태:', JSON.stringify(st), '| 할 일:', JSON.stringify(st.goal ? ai.todo(st.goal) : []).slice(0, 400));
      return '막힘(진척 없음)';
    }
    if (st.cleared.length >= ai.fields().length) return '모두 깸';

    equipBest();

    // 목표가 없으면 하나 건다 — 가장 센 무기 · 방어구 쪽
    if (!st.goal){
      const cands = ai.candidates();
      if (cands.length){
        const pick = g(`(function(){
          const list = ${JSON.stringify(cands)};
          const val = t => { const d = DEFS[t] || {}; return (d.atk || 0) * 3 + (d.def || 0) * 2 + (d.pierce ? 6 : 0) + (d.bleed || 0) * 3 + (d.heal || 0) * 2; };
          const slotOf = t => (ALL_SLOTS.find(sl => useOf(t).includes(sl.tag)) || {}).key || null;
          let bT = null, bV = 0;
          for (const t of list){
            const k = slotOf(t);
            const now = k ? equipped(k) : null;
            const gain = val(t) - (now ? val(now) : 0);            // 지금 쥔 것보다 나아야 건다
            if (!k || have(t) > 0) continue;
            if (gain > bV){ bV = gain; bT = t; }
          }
          return bT;
        })()`);
        if (pick){ ai.goal(pick); note(`목표 ${pick}`); continue; }
      }
    }

    // 목표 차례에서 **지금 할 수 있는 걸음**을 하나 민다 (만들기 먼저, 없으면 주우러)
    if (st.goal){
      const todo = ai.todo(st.goal);
      let did = false;
      for (const x of todo){                                       // ① 지금 만들 수 있는 것
        if (x.kind !== 'make' || !x.r || !x.r.a || !x.r.b) continue;
        const a = x.r.a.card, b = x.r.b.card;
        if (a && b && ai.craft(a, b)){ ai.touch(); note(`조합 ${x.type}`); did = true; break; }
      }
      if (did) continue;
      for (const x of todo){                                       // ② 지금 갈 수 있는 땅에서 주울 것
        if (x.kind !== 'get') continue;
        const f = fieldFor(x.type);
        if (!f) continue;
        ai.restTo(0.9); ai.touch();
        if (ai.sortie(f) === 'go'){ ai.finishExp(); note(`원정 ${f} (${x.type})`); did = true; break; }
      }
      if (did) continue;
      if (!todo.length){                                           // ③ 다 모였는데 목표가 안 끝났으면 마지막 조합
        const last = ai.plan(st.goal).filter(x => x.kind === 'make').pop();
        if (last && last.r && last.r.a && last.r.b && ai.craft(last.r.a.card, last.r.b.card)){ ai.touch(); note(`조합 ${last.type}`); continue; }
      }
    }

    // 다음 땅 도전 — 못 깬 곳 중 앞선 것. 세 번 지면 더 세질 때까지 쉬어 간다
    const next = ai.fields().find(f => !f.locked && !st.cleared.includes(f.id));
    if (next){
      const fails = downs[next.id] || 0;
      if (fails >= 3 && st.goal){ ai.advance(20000); continue; }    // 장비부터 갖추러 돌아감
      ai.restTo(1); ai.touch();
      if (ai.sortie(next.id) === 'go'){
        const hpBefore = ai.state().hp;
        ai.finishExp();
        const after = ai.state();
        if (after.hp <= 0 || hpBefore > after.hp && !after.cleared.includes(next.id)) downs[next.id] = fails + 1;
        if (after.cleared.includes(next.id)) downs[next.id] = 0;
        note(`원정 ${next.id} (도전)`);
        continue;
      }
    }
    ai.advance(5000);                                             // 할 게 없으면 잠깐 쉰다
  }
  return '걸음 한계';
}

function runOnce(seed){
  const boot0 = boot(seed);
  const ai = makeAI(boot0);
  const marks = [];
  const note = txt => { if (VERBOSE) console.log(`   [${ai.minutes().toFixed(1)}분] ${txt}`); };
  const why = play(ai, note);
  const log = ai.log();
  const ev = log.ev || [];
  const firstAt = (k, test) => { const e = ev.find(x => x.k === k && (!test || test(x))); return e ? +(e.t / 60000).toFixed(1) : null; };
  return {
    seed, why,
    분: +ai.minutes().toFixed(1),
    논시간_분: +(log.active / 60000).toFixed(1),
    원정시간_분: +(log.expTime / 60000).toFixed(1),
    깬땅: (ai.state().cleared || []),
    레벨: ai.state().lv,
    발견카드: ai.state().seen,
    원정: ev.filter(e => e.k === 'expStart').length,
    쓰러짐: ev.filter(e => e.k === 'expEnd' && e.how === 'down').length,
    막힘: ev.filter(e => e.k === 'blocked').length,
    첫무기_분: firstAt('craft', e => e.out && e.out.some(o => ['stoneknife', 'toothdagger', 'fangspear'].includes(o))),
    곰잡은_분: firstAt('kill', e => e.foe === 'bear'),
    땅클리어_분: ev.filter(e => e.k === 'expEnd' && e.how === 'boss').map(e => `${e.field}:${(e.t / 60000).toFixed(1)}`),
    목표수: ev.filter(e => e.k === 'goalDone').length,
    목표달성: ev.filter(e => e.k === 'goalDone').slice(0, 8).map(e => `${e.type}:${((e.aMs - e.xMs) / 60000).toFixed(1)}분`),
    log,
  };
}

const runs = [];
for (let i = 0; i < RUNS; i++){
  const seed = SEED0 == null ? null : +SEED0 + i;
  const t0 = Date.now();
  const r = runOnce(seed);
  r.실제초 = +((Date.now() - t0) / 1000).toFixed(1);
  runs.push(r);
  const { log, ...show } = r;
  console.log(`— ${i + 1}판`, JSON.stringify(show, null, ' ').replace(/\n\s*/g, ' '));
}

if (RUNS > 1){
  const avg = k => +(runs.reduce((s, r) => s + (r[k] || 0), 0) / runs.length).toFixed(1);
  console.log('\n= 평균', JSON.stringify({
    분: avg('분'), 논시간_분: avg('논시간_분'), 원정: avg('원정'), 쓰러짐: avg('쓰러짐'), 막힘: avg('막힘'),
    레벨: avg('레벨'), 발견카드: avg('발견카드'), 깬땅수: +(runs.reduce((s, r) => s + r.깬땅.length, 0) / runs.length).toFixed(1),
    끝난까닭: runs.reduce((o, r) => (o[r.why] = (o[r.why] || 0) + 1, o), {}),
  }));
}

const out = arg('--json', null);
if (out){
  fs.writeFileSync(out, JSON.stringify(runs.length === 1 ? runs[0] : runs, null, 2), 'utf8');
  console.log('기록 저장:', out);
}
