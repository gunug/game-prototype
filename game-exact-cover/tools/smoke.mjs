/**
 * index.html 을 실제로 실행해 보는 스모크 테스트.
 *
 *   node tools/smoke.mjs
 *
 * 문법만 보는 검사는 "정의가 통째로 사라진" 종류의 사고를 못 잡는다. 실제로
 * readField 가 없어진 채 배포돼서 화면이 비어 나갔다. 그래서 DOM 을 최소한만
 * 흉내내고 스크립트를 끝까지 돌린 뒤, 눈에 보여야 할 것들을 센다.
 */

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const GAME = path.join(HERE, '..', 'index.html');

/* ── 최소 DOM ── */

class Style {
  setProperty(name, value) { this[name] = String(value); }
  removeProperty(name) { delete this[name]; }
}

class ClassList {
  constructor(el) { this.el = el; this.set = new Set(); }
  add(...names) { names.forEach((n) => this.set.add(n)); }
  remove(...names) { names.forEach((n) => this.set.delete(n)); }
  contains(name) { return this.set.has(name); }
  toggle(name, on) { (on ? this.set.add(name) : this.set.delete(name)); }
}

class El {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.style = new Style();
    this.classList = new ClassList(this);
    this.attrs = {};
    this.handlers = {};
    this.textContent = '';
  }
  get className() { return [...this.classList.set].join(' '); }
  set className(v) {
    this.classList.set = new Set(String(v).split(/\s+/).filter(Boolean));
  }
  appendChild(node) {
    if (node instanceof Frag) { node.children.forEach((c) => this.children.push(c)); return node; }
    this.children.push(node);
    return node;
  }
  append(...nodes) { nodes.forEach((n) => this.appendChild(n)); }
  replaceChildren(node) { this.children = []; if (node) this.appendChild(node); }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name] ?? null; }
  addEventListener(type, fn) { (this.handlers[type] ??= []).push(fn); }
  dispatch(type, event) { (this.handlers[type] || []).forEach((fn) => fn(event)); }
  setPointerCapture() {}
  releasePointerCapture() {}
  closest() { return null; }
  getBoundingClientRect() { return { left: 0, top: 0, width: 800, height: 800 }; }
}

class Frag extends El {
  constructor() { super('#fragment'); }
}

const nodes = {};
for (const id of ['grid', 'board', 'preview', 'banner', 'reset',
                  'outline', 'outline-path', 'select', 'play', 'groups',
                  'progress', 'stage-name', 'stage-diff', 'back', 'next']) {
  nodes[id] = new El('div');
  nodes[id].attrs.id = id;
}

const store = new Map();

// 타이머는 직접 돌린다. 3초 홀드를 실제로 기다리지 않고 검사하기 위해서다.
const timers = new Map();
let timerId = 0;
const runTimers = () => {
  const due = [...timers.values()];
  timers.clear();
  due.forEach((fn) => fn());
};

const sandbox = {
  document: {
    getElementById: (id) => nodes[id] ?? null,
    createElement: (tag) => new El(tag),
    createDocumentFragment: () => new Frag(),
  },
  window: { addEventListener() {}, innerWidth: 900, innerHeight: 900 },
  localStorage: {
    getItem: (key) => (store.has(key) ? store.get(key) : null),
    setItem: (key, value) => store.set(key, String(value)),
  },
  console,
  setTimeout: (fn) => { timers.set(++timerId, fn); return timerId; },
  clearTimeout: (id) => timers.delete(id),
};
sandbox.window.localStorage = sandbox.localStorage;

/* ── 실행 ── */

const js = fs.readFileSync(GAME, 'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
const run = new Function(...Object.keys(sandbox), js);

const fails = [];
const check = (label, ok, detail = '') => {
  console.log(`  ${ok ? 'OK  ' : '실패'} ${label}${detail ? ' — ' + detail : ''}`);
  if (!ok) fails.push(label);
};

try {
  run(...Object.values(sandbox));
} catch (err) {
  console.log(`  실패 스크립트 실행 — ${err.message}`);
  process.exit(1);
}

const grid = nodes.grid;

/* ── 퍼즐 고르는 페이지 ── */

check('처음엔 목록 화면', nodes.play.attrs.hidden !== undefined || nodes.play.hidden === true,
  `play.hidden=${nodes.play.hidden}`);

const sections = nodes.groups.children;
check('모드별 묶음', sections.length === 2,
  sections.map((sec) => sec.children[0].textContent).join(' / '));

const cards = sections.flatMap((sec) => sec.children[1].children.map((li) => li.children[0]));
check('퍼즐 카드', cards.length > 0, `${cards.length}개`);
check('진행 표시', /\d+ \/ \d+/.test(nodes.progress.textContent), nodes.progress.textContent);

const cardDiff = (b) => {
  const badge = b.children[1].children.find((c) => c.classList.contains('diff'));
  return badge ? Number(badge.textContent) : NaN;
};
check('카드마다 난이도', cards.every((b) => Number.isFinite(cardDiff(b))));
check('난이도 1~100', cards.every((b) => cardDiff(b) >= 1 && cardDiff(b) <= 100));

const runs = sections.map((sec) =>
  sec.children[1].children.map((li) => cardDiff(li.children[0])));
check('구간별 난이도 오름차순',
  runs.every((run) => run.every((d, i) => i === 0 || run[i - 1] <= d)),
  runs.map((r) => r.join(' ')).join('  |  '));

check('카드에 모양 칩', cards.every((b) => b.children[1].children[0].children.length > 0));

/* ── 퍼즐 열기 ── */

cards[0].dispatch('click', {});
check('퍼즐 열면 게임 화면', nodes.play.hidden === false && nodes.select.hidden === true,
  `play=${nodes.play.hidden} select=${nodes.select.hidden}`);
check('퍼즐 이름 표시', !!nodes['stage-name'].textContent, nodes['stage-name'].textContent);

const tiles = grid.children.filter((t) => t.classList.contains('tile'));
check('격자 100칸', tiles.length === 100, `${tiles.length}칸`);

const fieldTiles = tiles.filter((t) => t.classList.contains('field'));
check('활성 칸 있음', fieldTiles.length > 0, `${fieldTiles.length}칸`);

const chips = nodes.preview.children;
check('모양 미리보기', chips.length > 0 && chips[0].children.length > 0,
  `${chips.length}개, 첫 칩 ${chips[0] ? chips[0].children.length : 0}칸`);

const d = nodes['outline-path'].getAttribute('d') || '';
check('필드 외곽선', d.startsWith('M') && d.length > 20, `${d.length}자`);

// 활성 칸 하나를 실제로 눌러 칠해지는지
const cell = 80;   // getBoundingClientRect 가 0,0 이고 칸은 80px 로 잡힌다
const first = tiles.findIndex((t) => t.classList.contains('field'));
const fc = first % 10, fr = Math.floor(first / 10);
nodes.board.dispatch('pointerdown', {
  button: 0, pointerType: 'mouse', pointerId: 1,
  clientX: fc * cell + cell / 2, clientY: fr * cell + cell / 2,
  target: { closest: () => null }, preventDefault() {},
});
nodes.board.dispatch('pointerup', {});
check('클릭하면 칠해짐', !!tiles[first].style.backgroundColor,
  tiles[first].style.backgroundColor || '색 없음');

// 목표 모양(스테이지 1은 2x2 정사각형)을 통째로 칠하면 유리 질감이 붙어야 한다
const isField = (c, r) =>
  c >= 0 && r >= 0 && c < 10 && r < 10 && tiles[r * 10 + c].classList.contains('field');
let block = null;
for (let r = 0; r < 9 && !block; r++)
  for (let c = 0; c < 9 && !block; c++)
    if (isField(c, r) && isField(c + 1, r) && isField(c, r + 1) && isField(c + 1, r + 1))
      block = [c, r];

if (!block) {
  check('2x2 블록 찾음', false);
} else {
  const [bc, br] = block;
  const at = (c, r) => ({ clientX: c * cell + cell / 2, clientY: r * cell + cell / 2 });
  nodes.board.dispatch('pointerdown', {
    button: 0, pointerType: 'mouse', pointerId: 2, ...at(bc, br),
    target: { closest: () => null }, preventDefault() {},
  });
  nodes.board.dispatch('pointermove', at(bc + 1, br));
  nodes.board.dispatch('pointermove', at(bc + 1, br + 1));
  nodes.board.dispatch('pointermove', at(bc, br + 1));
  nodes.board.dispatch('pointerup', {});

  const square = [[bc, br], [bc + 1, br], [bc, br + 1], [bc + 1, br + 1]];
  const marked = square.filter(([c, r]) => tiles[r * 10 + c].classList.contains('match'));
  check('모양 일치하면 유리 질감', marked.length === 4, `${marked.length}/4칸`);

  // 칠해진 칸을 홀드하면 그 색 전체가 지워져야 한다
  nodes.board.dispatch('pointerdown', {
    button: 0, pointerType: 'mouse', pointerId: 3, ...at(bc, br),
    target: { closest: () => null }, preventDefault() {},
  });
  const marking = square.filter(([c, r]) => tiles[r * 10 + c].classList.contains('holding'));
  check('홀드 중 표시', marking.length === 4, `${marking.length}/4칸`);

  runTimers();
  const left = square.filter(([c, r]) => tiles[r * 10 + c].style.backgroundColor);
  check('홀드하면 같은 색 전부 지워짐', left.length === 0, `${left.length}칸 남음`);

  nodes.board.dispatch('pointerup', {});
  const stillHolding = tiles.filter((t) => t.classList.contains('holding'));
  check('홀드 표시 정리됨', stillHolding.length === 0, `${stillHolding.length}칸`);

  // 다시 칠하고, 칸을 옮기면 홀드가 취소되는지
  const press = (c, r, id) => nodes.board.dispatch('pointerdown', {
    button: 0, pointerType: 'mouse', pointerId: id, ...at(c, r),
    target: { closest: () => null }, preventDefault() {},
  });
  press(bc, br, 4);
  nodes.board.dispatch('pointermove', at(bc + 1, br));
  nodes.board.dispatch('pointerup', {});

  press(bc, br, 5);                            // 칠해진 칸에서 다시 시작
  nodes.board.dispatch('pointermove', at(bc + 1, br));
  runTimers();                                 // 옮겼으니 홀드는 안 터져야 한다
  const kept = [[bc, br], [bc + 1, br]].filter(([c, r]) => tiles[r * 10 + c].style.backgroundColor);
  check('옮기면 홀드 취소', kept.length === 2, `${kept.length}/2칸 남음`);
  nodes.board.dispatch('pointerup', {});

  // 짧게 누르면 그 칸만 지워진다
  press(bc, br, 6);
  nodes.board.dispatch('pointerup', {});
  const one = !tiles[br * 10 + bc].style.backgroundColor
    && !!tiles[br * 10 + bc + 1].style.backgroundColor;
  check('짧게 누르면 한 칸만 지워짐', one);
}

// 목록으로 돌아가기
nodes.back.dispatch('click', {});
check('뒤로 가면 목록', nodes.select.hidden === false && nodes.play.hidden === true);

// 두 종 스테이지를 열면 모양 칩이 둘 나와야 한다
const dualSec = nodes.groups.children.find((sec) => sec.children[0].textContent.includes('두 종'));
if (!dualSec) {
  check('두 종 묶음 있음', false);
} else {
  dualSec.children[1].children[0].children[0].dispatch('click', {});
  check('두 종은 모양 2개', nodes.preview.children.length === 2,
    `${nodes.preview.children.length}개`);
  const dualField = grid.children.filter((t) => t.classList.contains('field'));
  check('두 종 필드 로드', dualField.length > 0, `${dualField.length}칸`);
}

// 클리어 배너와 다음 버튼
check('처음엔 배너 숨김', !nodes.banner.classList.contains('show'));

const before = nodes['stage-name'].textContent;
nodes.next.dispatch('click', {});
check('다음 버튼이 다음 퍼즐을 연다',
  nodes['stage-name'].textContent !== before && nodes.play.hidden === false,
  `${before} -> ${nodes['stage-name'].textContent}`);

if (fails.length) {
  console.log(`\n${fails.length}건 실패`);
  process.exit(1);
}
console.log('\n전부 통과');
