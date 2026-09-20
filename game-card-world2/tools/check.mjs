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

// 4) 저장 → **새로 고침** (v0.76.0)
//   저장을 남긴 뒤 스크립트를 처음부터 다시 돌려 본다. 시작 코드에서 load()가 조용히 실패하면
//   (예: 아직 선언 전인 전역을 건드려 TDZ 오류 → catch가 삼킴) 진행이 통째로 버려진다
try {
  vm.runInContext("S.seen = ['stone','flint']; S.knight.lv = 6; S.knight.xp = 7; S.killed = ['wolf']; save();", ctx);
  const ctx2 = { ...ctx };                                        // 같은 localStorage(mem)를 쓰는 새 판
  ctx2.document = fake('document');
  ctx2.setTimeout = () => 0; ctx2.setInterval = () => 0; ctx2.requestAnimationFrame = () => 0;
  ctx2.window = ctx2; ctx2.globalThis = ctx2; ctx2.self = ctx2;
  vm.createContext(ctx2);
  vm.runInContext(code, ctx2, { filename: 'index.html<script> (새로 고침)' });
  const got = vm.runInContext('JSON.stringify({ lv: S.knight.lv, xp: S.knight.xp, seen: S.seen.length })', ctx2);
  const g = JSON.parse(got);
  if (g.lv !== 6 || g.xp !== 7 || g.seen !== 2){
    report('새로 고침', new Error('저장이 버려짐 — 새로 고치면 처음부터 시작됨: ' + got));
  } else console.log('✓ 저장 → 새로 고침');
} catch (e){ report('새로 고침', e); }

setTimeout(() => { console.log(fail ? `\n오류 ${fail}개` : '\n오류 없음'); process.exit(fail ? 1 : 0); }, 50);
