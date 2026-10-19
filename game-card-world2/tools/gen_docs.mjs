// 카드 목록 · 조합식 문서 만들기 — index.html 의 데이터(DEFS · CRAFT_RECIPES · FIELD_YIELDS · ENEMIES)를 그대로 읽어 쓴다
// 사용: node tools/gen_docs.mjs   (게임 폴더에서) → docs/카드_목록.md · docs/조합식.md 를 덮어쓴다
//   손으로 고치지 않는다 — 데이터가 바뀌면 다시 돌린다
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const DIR = path.join(path.dirname(fileURLToPath(import.meta.url)), '..');
const html = fs.readFileSync(path.join(DIR, 'index.html'), 'utf8');
const code = [...html.matchAll(/<script(?![^>]*\bsrc=)[^>]*>([\s\S]*?)<\/script>/g)].map(m => m[1]).join('\n;\n');

// 가짜 DOM (check.mjs 와 같은 얼개)
function fake(){
  const st = {};
  return new Proxy(function(){}, {
    get(_, k){
      if (k === Symbol.toPrimitive) return h => h === 'string' ? '' : 0;
      if (k === 'then') return undefined;
      if (k === Symbol.iterator) return function*(){};
      if (k in st) return st[k];
      if (k === 'length') return 0;
      return (st[k] = fake());
    },
    set(_, k, v){ st[k] = v; return true; },
    apply(){ return fake(); }, construct(){ return fake(); },
  });
}
const ctx = { console: { log(){}, warn(){}, error(){} }, Math, JSON, Date, Object, Array, Set, Map, String, Number, Boolean, RegExp, Promise, Symbol, Error,
  parseInt, parseFloat, isNaN, Infinity, structuredClone,
  window: fake(), document: fake(), navigator: fake(), location: fake(),
  localStorage: { getItem(){ return null; }, setItem(){}, removeItem(){} },
  performance: { now: () => 0 }, setTimeout(){ return 0; }, clearTimeout(){}, setInterval(){ return 0; }, clearInterval(){},
  requestAnimationFrame(){ return 0; }, addEventListener(){}, removeEventListener(){}, getComputedStyle: () => fake(), matchMedia: () => fake(),
  innerWidth: 1280, innerHeight: 800, devicePixelRatio: 1, Image: function(){},
  ResizeObserver: function(){ return { observe(){} }; }, IntersectionObserver: function(){ return { observe(){} }; } };
ctx.globalThis = ctx; ctx.self = ctx;
vm.createContext(ctx);
vm.runInContext(code, ctx);

const data = JSON.parse(vm.runInContext(`JSON.stringify((function(){
  const STAT = [['atk','공격'],['def','방어'],['hp','체력'],['spd','이동'],['range','사거리'],['aps','공속'],['bleed','출혈'],['heal','회복']];
  const statOf = d => STAT.filter(([k]) => d[k]).map(([k, n]) => n + ' ' + d[k]).concat(d.pierce ? ['방어 무시'] : []).join(' · ');
  const name = t => (DEFS[t] || {}).name || t;
  const recs = CRAFT_RECIPES.filter(r => !r.cook && r.a.card && r.b.card).map(r => ({ id: r.id, a: r.a.card, b: r.b.card, out: r.out || [], tab: recipeKind(r) }));
  const cards = CRAFT_TYPES.map(t => ({ id: t, name: name(t), step: DEFS[t].step || 0, kind: DEFS[t].kind,
    stat: statOf(DEFS[t]), use: useOf(t), desc: DESC[t] || '' }));
  const fields = FIELDS.map(f => ({ id: f.id, name: f.name, emoji: f.emoji, kind: fieldUse(f), yields: yieldsOf(f.id) }));
  const drops = {};
  for (const k in ENEMIES) for (const l of (ENEMIES[k].loot || [])) (drops[l[0]] = drops[l[0]] || []).push(ENEMIES[k].name + ' ' + l[1] + '%');
  const boards = Object.fromEntries(BOARDS.map(b => [b.id, b.name]));
  return { version: VERSION, recs, cards, fields, drops, boards, names: Object.fromEntries(CRAFT_TYPES.map(t => [t, name(t)])) };
})())`, ctx));

const { version, recs, cards, fields, drops, boards, names } = data;
const N = t => names[t] || t;
const byId = Object.fromEntries(cards.map(c => [c.id, c]));
const gathered = new Map();                                       // 채집품 → 땅
for (const f of fields) for (const t of f.yields) gathered.set(t, f);
const madeBy = {};                                                // 결과 → 조합식들
for (const r of recs) for (const o of r.out) (madeBy[o] = madeBy[o] || []).push(r);
const usedIn = {};                                                // 재료 → 결과들
for (const r of recs) for (const x of [r.a, r.b]) (usedIn[x] = usedIn[x] || new Set()).add(r.out.map(N).join(' · '));
const cell = s => String(s || '').replace(/\|/g, '/');
const use = c => c.use.join(' · ');
const today = new Date().toISOString().slice(0, 10);
const head = (title) => `# ${title} — 카드 월드 RPG 2\n\n> **${version}** 기준 · ${today} · \`node tools/gen_docs.mjs\` 로 만든 문서 — **손으로 고치지 않는다** (데이터가 바뀌면 다시 돌린다)\n`;

// ── 카드 목록
let A = head('카드 목록');
A += `> 그림은 모두 \`images/icon/card_<id>.png\`. 단계(step) 1 = 날것, 2부터 조합으로 만든다.\n\n`;
A += `## 1. 채집품 — 땅마다 (겹치지 않는다)\n\n원정 중 채집 지점에서 줍는다. 땅마다 달라서 같은 것이 두 땅에서 나오지 않는다 (\`check.mjs\` 가 본다).\n\n`;
for (const f of fields){
  if (!f.yields.length) continue;
  A += `### ${f.emoji} ${f.name} (${f.kind})\n\n| id | 이름 | 쓰임 | 설명 |\n|---|---|---|---|\n`;
  for (const t of f.yields){ const c = byId[t]; A += `| \`${t}\` | ${c.name} | ${cell(use(c))} | ${cell(c.desc)} |\n`; }
  A += '\n';
}
const dropOnly = cards.filter(c => c.step <= 1 && !gathered.has(c.id) && drops[c.id]);
A += `## 2. 떨구는 것 — 크리처에게서\n\n크리처를 쓰러뜨리면 확률로 나온다. 여러 크리처가 같은 것을 떨굴 수 있다.\n\n| id | 이름 | 떨구는 크리처 | 쓰임 | 설명 |\n|---|---|---|---|---|\n`;
for (const c of dropOnly) A += `| \`${c.id}\` | ${c.name} | ${cell(drops[c.id].join(', '))} | ${cell(use(c))} | ${cell(c.desc)} |\n`;
A += '\n## 3. 만드는 것 — 단계별\n\n';
const made = cards.filter(c => madeBy[c.id]);
const steps = [...new Set(made.map(c => c.step))].sort((a, b) => a - b);
for (const st of steps){
  A += `### ${st}단계\n\n| id | 이름 | 탭 | 조합식 | 수치 | 쓰임 | 설명 |\n|---|---|---|---|---|---|---|\n`;
  for (const c of made.filter(c => c.step === st)){
    const rs = madeBy[c.id];
    A += `| \`${c.id}\` | ${c.name} | ${cell(boards[rs[0].tab] || rs[0].tab)} | ${cell(rs.map(r => N(r.a) + ' + ' + N(r.b)).join(' / '))} | ${cell(c.stat)} | ${cell(use(c))} | ${cell(c.desc)} |\n`;
  }
  A += '\n';
}
const other = cards.filter(c => !gathered.has(c.id) && !drops[c.id] && !madeBy[c.id]);
if (other.length){
  A += `## 4. 나오는 곳이 없는 카드\n\n데이터엔 있지만 지금은 얻을 길이 없다.\n\n`;
  A += other.map(c => `\`${c.id}\` ${c.name}`).join(' · ') + '\n';
}
fs.writeFileSync(path.join(DIR, 'docs', '카드_목록.md'), A);

// ── 조합식
let B = head('조합식');
B += `\n## 규칙\n\n- 카드를 끌어 다른 카드 위에 놓으면 조합. 어느 쪽을 끌어도 같다.\n`
  + `- 조합식은 탭마다 있다. 그 탭을 맡은 장인이 여관에서 합류해야 그 탭에서 만든다 (조합 탭은 처음부터).\n`
  + `- **같은 두 재료의 결과는 하나뿐.** 같은 결과로 가는 길은 여럿일 수 있다 (땅마다 다른 재료로).\n`
  + `- **단계 규칙** — 결과 단계 = 두 재료 가운데 높은 단계 + 1, 두 재료의 단계 차는 1 이하.\n`
  + `- 무기끼리는 합치지 않는다 (무기 + 무기재료만).\n`
  + `- 위 규칙은 \`node tools/check.mjs\` 가 검사한다.\n\n`;
B += `## 목록 (${recs.length}개) — 탭별\n\n`;
const tabs = [...new Set(recs.map(r => r.tab))];
for (const tb of tabs){
  const list = recs.filter(r => r.tab === tb);
  B += `### ${boards[tb] || tb} (${list.length})\n\n| A | B | 결과 | 단계 |\n|---|---|---|---|\n`;
  for (const r of list) B += `| ${N(r.a)} | ${N(r.b)} | ${r.out.map(N).join(' · ')} | ${r.out.map(o => (byId[o] || {}).step || '').join(' · ')} |\n`;
  B += '\n';
}
B += `## 날것이 쓰이는 곳 (1단계)\n\n`;
for (const c of cards.filter(c => c.step <= 1)){
  const where = gathered.has(c.id) ? `${gathered.get(c.id).emoji} ${gathered.get(c.id).name}` : drops[c.id] ? '떨굼' : '—';
  B += `- **${c.name}** (${where}) — ${usedIn[c.id] ? [...usedIn[c.id]].join(', ') : '_아직 쓰이는 곳 없음_'}\n`;
}
const unused = cards.filter(c => !usedIn[c.id] && c.kind !== 'gear');
B += `\n## 다른 조합에 쓰이지 않는 카드 (장비 제외)\n\n${unused.map(c => c.name).join(' · ') || '없음'}\n`;
fs.writeFileSync(path.join(DIR, 'docs', '조합식.md'), B);

console.log(`카드 ${cards.length} · 조합식 ${recs.length} → docs/카드_목록.md · docs/조합식.md (${version})`);
