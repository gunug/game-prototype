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
// v7.15.0: --blind = **아는 것만 쓴다**.
//   · 해 본 적 없고 두 재료를 다 본 적도 없는 조합은 모른다 (게임의 cardKnown 규칙 그대로)
//   · 떨구는 것은 **한 번 받아 봐야** 어디서 나오는지 안다 (게임의 lootKnown 규칙 그대로)
//   · 손질 시간을 매긴다 — 탭 옮기기 1.2초 · 조합 2.5초 · 목표 고르기 9초(첫 번째 25초)
//     이 시간은 원정이 아닌 시간이라 로그에서 곧바로 '헤맴(aMs − xMs)' 으로 잡힌다
const BLIND = has('--blind');
const COST = { tab: 1200, craft: 2500, equip: 2000, goal: 9000, goalFirst: 25000, sortie: 1500, think: 2500 };

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
    firstGoal: false,
    spend(ms){ if (BLIND){ this.touch(); clock.advance(ms); } },   // 눈으로 찾고 끌어다 놓는 시간
    knowsRecipe(a, b){                                             // 그 조합을 아는가
      if (!BLIND) return true;
      return g(`(function(){
        const A = ${JSON.stringify(a)}, B = ${JSON.stringify(b)};
        const r0 = CRAFT_RECIPES.find(r => !r.cook
          && ((sideMatch(r.a, A) && sideMatch(r.b, B)) || (sideMatch(r.a, B) && sideMatch(r.b, A))));
        if (!r0) return false;
        if ((S.madeRecipes || []).includes(r0.id)) return true;    // 해 본 조합
        return S.seen.includes(A) && S.seen.includes(B);           // 두 재료를 다 봤으면 해 볼 수 있다
      })()`);
    },
    knownSource(type){                                             // 그 재료를 어디서 얻는지 아는가
      const blind = BLIND ? 'true' : 'false';
      this.srcAsk = (this.srcAsk || 0) + 1;
      return g(`(function(){
        const t = ${JSON.stringify(type)}, blind = ${blind}, out = [];
        for (const f of FIELDS){
          if (fieldLocked(f.id) || f.raid) continue;               // v9.43.0: 레이드는 재료 벌러 가는 곳이 아니다
          if (f.id === 'prelude' && (S.cleared || []).includes('prelude')) continue;
          if (yieldsOf(f.id).includes(t)){ out.push(f.id); continue; }   // 줍는 것은 목표 차례가 알려 준다
          if (lootTypes(f.id).includes(t) && (!blind || lootKnown(f.id, t))) out.push(f.id);   // 떨구는 것은 받아 봐야 안다
        }
        return JSON.parse(JSON.stringify(out));
      })()`);
    },
    state(){
      return g(`(function(){
        const cards = {}; for (const c of S.cards) if (c.n > 0) cards[c.type] = (cards[c.type] || 0) + c.n;
        return JSON.parse(JSON.stringify({
          lv: S.knight.lv, hp: S.knight.hp, maxhp: knightMaxHp(), atk: knightAtk(), def: knightDef(),
          exp: !!exp, tab: S.tab, goal: S.goal, cards, seen: S.seen.length,
          equip: S.equip, cleared: S.cleared || [],
          fields: FIELDS.filter(f => !fieldLocked(f.id) && !f.raid).map(f => f.id),   // v9.43.0: 레이드는 AI 가 안 간다
          quests: (S.quests || []).filter(q => !q.done).map(q => q.id),
        }));
      })()`);
    },
    // 재료 둘을 합친다 — 손으로 끌어다 놓는 것과 같은 길
    craft(a, b){
      // 사람이 하듯 **그 조합을 할 수 있는 탭으로 먼저 옮긴 뒤** 합친다
      if (!this.knowsRecipe(a, b)){ this.unknownCraft = (this.unknownCraft || 0) + 1; return false; }   // v7.15.0: 모르는 조합
      this.spend(COST.craft);
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
    goal(t){ this.spend(this.firstGoal ? COST.goal : COST.goalFirst); this.firstGoal = true; return call('setGoal', t); },
    plan(t){ return g(`JSON.parse(JSON.stringify(goalSteps(${JSON.stringify(t)})))`); },
    // 아직 안 끝난 걸음들 (게임의 판정을 그대로 쓴다)
    todo(t){ return g(`JSON.parse(JSON.stringify(goalSteps(${JSON.stringify(t)}).filter(st => !planStepDone(st))))`); },
    candidates(){ return g(`JSON.parse(JSON.stringify(aimCandidates()))`); },
    equip(slot, type){ this.spend(COST.equip); return g(`(function(){ const sl = slotByKey(${JSON.stringify(slot)}); if (!sl || !slotOpen(sl.key)) return false;
      if (!(have(${JSON.stringify(type)}) > 0)) return false; equipCard(sl, ${JSON.stringify(type)}); return true; })()`); },
    tab(id){ this.spend(COST.tab); return call('setTab', id); },
    sortie(field){
      const before = g('!!exp');
      if (before) return 'busy';
      this.spend(COST.sortie);
      call('expStart', field, ctx.document.createElement('div'));   // flash() 가 만질 가짜 카드
      return g('!!exp') ? 'go' : 'blocked';
    },
    // 원정이 끝날 때까지 시간을 흘려 보낸다. between() 를 주면 **원정이 도는 사이에** 그 일을 한다
    //   (사람 기록을 보면 원정은 자동이라 그동안 조합 · 장비를 만진다 — 그 리듬을 흉내 낸다)
    finishExp(between){
      for (let i = 0; i < 600 && g('!!exp'); i++){
        clock.advance(500);
        if (between && i % 6 === 5) between();                     // 3초쯤마다 한 번 손을 놀린다
      }
      clock.advance(3000);                                         // 끝맺음 타이머(귀환 · 대사)
      return !g('!!exp');
    },
    // 그 땅을 지금 넘을 만한가 — 대본의 적들과 실제 규칙(방어 무시 · 출혈 · 회복)으로 셈해 본다
    canBeat(field){
      return g(`(function(){
        const plan = planOf(${JSON.stringify(field)});
        const foes = plan.filter(e => e.fight).map(e => ENEMIES[e.fight]);
        const pierce = knightPierce(), bleed = knightBleed();
        let hp = knightMaxHp();
        for (const f of foes){
          let fhp = f.hp, beats = 0;
          while (fhp > 0 && beats < 200){
            beats++;
            fhp -= Math.max(1, knightAtk() - (pierce ? 0 : f.def));
            if (fhp > 0){ if (bleed) fhp -= bleed; else if (f.regen) fhp = Math.min(f.hp, fhp + f.regen); }
            if (fhp <= 0) break;
            hp -= Math.max(1, f.atk - knightDef());
            if (hp <= 0) return false;
          }
          if (fhp > 0) return false;                               // 아무리 때려도 안 죽는 놈 (회복 기믹)
        }
        return true;
      })()`);
    },
    // 그 땅에 맞는 무기로 바꿔 쥔다 (회복하는 놈에겐 출혈, 단단한 놈에겐 방어 무시)
    // v9.50.0: 그 땅의 기믹에 **답이 되는 무기를 가졌나** — 없으면 지금은 갈 곳이 아니다
    //   (지금 AI 는 궁수를 쓸 줄 모른다. 사람은 궁수를 보내거나 활을 쥐면 된다)
    canAnswer(field){
      return g(`(function(){
        const foes = planOf(${JSON.stringify(field)}).filter(e => e.fight).map(e => ENEMIES[e.fight]);
        const mine = t => have(t) > 0 || equipped('weapon') === t;
        if (foes.some(f => f.thorns))
          return CRAFT_TYPES.some(t => useOf(t).includes('원거리무기') && mine(t));
        if (foes.some(f => f.shell))
          return CRAFT_TYPES.some(t => useOf(t).includes('근접무기') && (DEFS[t].aps || 1) * (DEFS[t].multi || 1) >= 2 && mine(t));
        return true;
      })()`);
    },
    // v9.50.0: 그 땅의 기믹을 푸는 무기 하나 — 만들 줄 아는 것 가운데 가장 싼 것
    answerFor(field){
      return g(`(function(){
        const foes = planOf(${JSON.stringify(field)}).filter(e => e.fight).map(e => ENEMIES[e.fight]);
        const want = foes.some(f => f.thorns) ? t => useOf(t).includes('원거리무기')
          : foes.some(f => f.shell) ? t => useOf(t).includes('근접무기') && (DEFS[t].aps || 1) * (DEFS[t].multi || 1) >= 2
          : null;
        if (!want) return null;
        const list = CRAFT_TYPES.filter(t => want(t) && have(t) <= 0 && aimReady(t))
          .sort((a, b) => (DEFS[a].step || 0) - (DEFS[b].step || 0));
        return list[0] || null;
      })()`);
    },
    armFor(field){
      return g(`(function(){
        const plan = planOf(${JSON.stringify(field)});
        const foes = plan.filter(e => e.fight).map(e => ENEMIES[e.fight]);
        const needBleed = foes.some(f => f.regen), needPierce = foes.some(f => f.def >= 9);
        const needRange = foes.some(f => f.thorns), needFast = foes.some(f => f.shell);   // v9.50.0: 되받음 · 껍질
        let bT = null, bV = -1;
        for (const t of CRAFT_TYPES){
          if (!useOf(t).some(u => u.indexOf('무기') >= 0)) continue;   // 활도 본다 (되받는 땅에서는 활이 답)
          if (!useOf(t).includes('근접무기') && !needRange) continue;
          const mine = have(t) > 0 || equipped('weapon') === t;
          if (!mine) continue;
          const d = DEFS[t];
          let v = (d.atk || 0);
          if (needBleed && d.bleed) v += 20;
          if (needPierce && d.pierce) v += 20;
          if (needRange && useOf(t).includes('원거리무기')) v += 30;   // 붙지 않는 것이 제일 크다
          if (needFast) v += (d.aps || 1) * (d.multi || 1) * 12;                       // 껍질은 때린 횟수로 깎인다
          if (v > bV){ bV = v; bT = t; }
        }
        if (bT && equipped('weapon') !== bT){ const sl = slotByKey('weapon'); if (have(bT) > 0) equipCard(sl, bT); }
        return equipped('weapon');
      })()`);
    },
    // v9.55.0: 여관 — 지금 등록된 사람 · 걸음 · 모자란 물건 · 등록할 수 있는 사람
    inn(){
      return g(`(function(){
        const n = S.inn || {}, reg = n.reg || null;
        const open = SMITHS.filter(x => !smithOk(x.id) && !smithLocked(x.id)).map(x => x.id);
        const step = reg ? smithStep(reg) : -1;
        const miss = [];
        if (reg && step === 1) for (const [t2] of (SMITH_BY_ID[reg].give || [])){
          const k = innGiveNeed(t2); if (k > 0) miss.push([t2, k]);
        }
        return JSON.parse(JSON.stringify({ reg, step, open, miss }));
      })()`);
    },
    smithLand(id){ return g(`(SMITH_BY_ID[${JSON.stringify(id)}] || {}).land || null`); },
    innReg(id){ this.spend(COST.tab); return g(`innRegister(${JSON.stringify(id)})`); },
    innHand(){                                                     // 가진 만큼 건넨다 — 건넨 장수를 돌려준다
      this.spend(COST.equip);
      return g(`(function(){
        const n = S.inn;
        if (!n || !n.reg || smithStep(n.reg) !== 1) return 0;
        let k = 0;
        for (const [t2] of (SMITH_BY_ID[n.reg].give || [])){
          for (let i = 0; i < 9 && innGiveNeed(t2) > 0 && have(t2) > 0; i++){ innGive(t2); k++; }
        }
        return k;
      })()`);
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
    fields(){ return g(`JSON.parse(JSON.stringify(FIELDS.filter(f => !f.raid).map(f => ({ id: f.id, name: f.name, dungeon: !!f.dungeon, locked: fieldLocked(f.id) }))))`); },
    log(){ return g('JSON.parse(JSON.stringify(LOG))'); },
    snapshot(){ return g('JSON.parse(JSON.stringify(progressSnapshot()))'); },
    smiths(){ return g('JSON.parse(JSON.stringify((S.inn || {}).done || []))'); },
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
  const fieldFor = type => {
    const f = (ai.knownSource(type) || [])[0] || null;
    if (!f) ai.unknownSource = (ai.unknownSource || 0) + 1;         // 어디서 나는지 모르는 재료
    return f;
  };
  let stuck = 0, lastSig = '';
  const downs = {}, raids = {};                                   // 땅마다 진 횟수 · 정찰 횟수
  // 원정이 도는 사이에 하는 일 — 목표 차례의 '지금 만들 수 있는 것'을 하나씩 (사람처럼)
  const craftStep = () => {
    const goal = ai.state().goal;
    if (!goal) return false;
    for (const x of ai.todo(goal)){
      if (x.kind !== 'make' || !x.r || !x.r.a || !x.r.b) continue;
      if (ai.craft(x.r.a.card, x.r.b.card)){ ai.touch(); note(`  (원정 중) 조합 ${x.type}`); return true; }
    }
    return false;
    return false;
  };
  for (let step = 0; step < 4000; step++){
    if (ai.minutes() > MAX_MIN) return '시간 한계';
    const st = ai.state();
    const sig = `${st.lv}|${st.cleared.length}|${st.seen}|${Object.keys(st.cards).length}|${st.goal}`;
    stuck = sig === lastSig ? stuck + 1 : 0;
    lastSig = sig;
    if (stuck > 200){
      if (VERBOSE) console.log('   막힘 상태:', JSON.stringify(st), '| 할 일:', JSON.stringify(st.goal ? ai.todo(st.goal) : []).slice(0, 400));
      return '막힘(진척 없음)';
    }
    if (st.cleared.length >= ai.fields().length) return '모두 깸';

    equipBest();

    // ① 목표가 없으면 하나 건다 — 지금 쥔 것보다 나은 장비
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
            if (!k || have(t) > 0 || aimFogged(t)) continue;   // v9.37.0: ??? (안개) 후보는 고르지 않는다 — 값을 알 수 없다
            const now = k ? equipped(k) : null;
            const gain = val(t) - (now ? val(now) : 0);
            if (gain > bV){ bV = gain; bT = t; }
          }
          return bT;
        })()`);
        if (pick){ ai.goal(pick); ai.touch(); note(`목표 ${pick}`); continue; }
      }
    }

    // ② 목표 차례 — 지금 만들 수 있으면 만든다
    if (st.goal && craftStep()) continue;

    // ②-2 v9.55.0: 여관 — 장인이 없으면 그 탭에서 아무것도 못 만든다. 한 명씩 등록하고 물건을 건넨다
    const inn = ai.inn();
    // 지금 넘을 만한 땅의 사람부터 찾는다 — 못 가는 땅의 물건을 요구받으면 그 자리에서 헛돈다
    // 힘이 되는 사람부터 — 요리사(음식)는 AI 에게 쓸모가 없어 맨 뒤로 민다
    const rank = id => (id === 'cook' || id === 'carpenter') ? 1 : 0;   // 음식 · 건축은 AI 에게 쓸모가 없다
    const openOrd = inn.open.slice().sort((a2, b2) => rank(a2) - rank(b2));
    const pick = openOrd.find(id => { const f = ai.smithLand(id); return !f || st.cleared.includes(f) || ai.canBeat(f); });
    if (!inn.reg && pick){ ai.innReg(pick); ai.touch(); note(`여관 등록 ${pick}`); continue; }
    if (inn.reg && inn.step === 1){
      if (ai.innHand() > 0){ ai.touch(); note('여관 납품'); continue; }
      const want = inn.miss[0] && fieldFor(inn.miss[0][0]);        // 모자란 물건이 나오는 땅으로
      if (want && ai.canBeat(want)){                               // 못 넘을 땅으로는 물건 벌러 가지 않는다
        ai.armFor(want); ai.restTo(1); ai.touch();
        if (ai.sortie(want) === 'go'){ ai.finishExp(craftStep); note(`원정 ${want} (여관 물건)`); continue; }
      }
    }

    // ③ 다음 땅: 넘을 만하면 간다. 아니면 **약한 땅에서 재료 · 경험치**를 벌어 온다 (사람도 그렇게 했다)
    const list = ai.fields().filter(f => !f.locked);
    const next = list.find(f => !st.cleared.includes(f.id));
    const target = next || list[list.length - 1];
    if (target){
      ai.armFor(target.id);                                        // 그 땅에 맞는 무기로
      // v9.50.0: 기믹에 답이 없으면(되받음엔 활, 껍질엔 빠른 무기) **그 무기를 먼저 목표로 건다**
      if (!ai.canAnswer(target.id)){
        const want = ai.answerFor(target.id);
        if (want && ai.state().goal !== want){ ai.goal(want); note(`기믹 대비 목표 ${want}`); }
      }
      const ok = ai.canBeat(target.id) && ai.canAnswer(target.id);
      let go = target.id;
      if (!ok){
        // 못 넘을 것 같으면 — 벌이(재료 · 경험치)와 **정찰**을 번갈아 한다.
        //   정찰 = 못 넘을 걸 알면서도 새 땅에 들어가 보는 것. 쓰러져도 줍는 것은 건지고, 거기서만 나오는
        //   재료(흑요석 …)를 손에 넣어야 다음 무기가 열린다 — 사람 기록도 이렇게 굴을 먼저 들이받았다
        raids[target.id] = raids[target.id] || 0;
        const scout = !st.cleared.includes(target.id) && (raids[target.id] % 3 === 0);
        if (scout){ raids[target.id]++; }
        else {
          raids[target.id]++;
          const need = st.goal ? ai.todo(st.goal).find(x => x.kind === 'get') : null;
          go = (need && fieldFor(need.type))
            || list.filter(f => st.cleared.includes(f.id) && ai.canBeat(f.id)).map(f => f.id).pop()
            || list[0].id;
          ai.armFor(go);
        }
      }
      ai.restTo(1); ai.touch();
      const hpBefore = ai.state().hp;
      if (ai.sortie(go) === 'go'){
        ai.finishExp(craftStep);                                   // 원정 중에도 조합
        const after = ai.state();
        if (after.cleared.includes(go)) downs[go] = 0;
        else if (after.hp <= 0) downs[go] = (downs[go] || 0) + 1;
        note(`원정 ${go}${ok ? '' : ' (벌이)'} — ${after.cleared.includes(go) ? '깸' : after.hp <= 0 ? '쓰러짐' : '귀환'}`);
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
    헤맴_분: +((log.active - log.expTime) / 60000).toFixed(1),      // 논 시간에서 원정을 뺀 것 = 화면 앞에서 손질한 시간
    장인: (ai.smiths() || []).length,                              // v9.55.0: 여관에서 찾아낸 사람 수 (무기 장인 포함)
    장인_분: ev.filter(e => e.k === 'inn-done').map(e => `${e.smith}:${(e.t / 60000).toFixed(1)}`),
    모르는조합: ai.unknownCraft || 0,
    모르는출처: ai.unknownSource || 0,
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
