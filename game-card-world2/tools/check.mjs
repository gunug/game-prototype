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
    const out = [], nm = t => DEFS[t].name, boards = BOARDS.filter(b => b.dyn).map(b => b.id);
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

setTimeout(() => { console.log(fail ? `\n오류 ${fail}개` : '\n오류 없음'); process.exit(fail ? 1 : 0); }, 50);
