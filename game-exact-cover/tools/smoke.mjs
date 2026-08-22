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
  replaceChildren(...nodes) { this.children = []; nodes.forEach((n) => n && this.appendChild(n)); }
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
    createTextNode: (text) => { const t = new El('#text'); t.textContent = String(text); return t; },
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

// 클리어한 퍼즐이 어떻게 보이는지 보려고 하나를 미리 클리어시켜 둔다
const CLEARED = '한 종 1';
store.set('exact-cover.cleared', JSON.stringify([CLEARED]));

/* ── 실행 ── */

const html = fs.readFileSync(GAME, 'utf8');
const css = html.match(/<style>([\s\S]*?)<\/style>/)[1];
const js = html.match(/<script>([\s\S]*?)<\/script>/)[1];

/**
 * 아무 조상도 안 붙은 `.foo { position: absolute }` 같은 규칙은 그 클래스를
 * 쓰는 다른 곳까지 끌고 간다. 클리어 배너가 .done 이었을 때 클리어한 카드가
 * 배너 자리로 튀어 나갔다. 자리를 옮기는 전역 클래스 규칙을 모아 둔다.
 */
const relocating = new Set();
const bareCss = css.replace(/\/\*[\s\S]*?\*\//g, '');   // 주석이 셀렉터에 딸려 오지 않게
for (const [, sel, body] of bareCss.matchAll(/([^{}]+)\{([^}]*)\}/g)) {
  if (!/position\s*:\s*(absolute|fixed)/.test(body)) continue;
  for (const one of sel.split(',')) {
    const m = one.trim().match(/^\.([\w-]+)(?:[.:][\w-]+)*$/);   // 조상 없는 단일 클래스
    if (m) relocating.add(m[1]);
  }
}

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
check('대분류 = 조각 종류 수', sections.length === 2,
  sections.map((sec) => sec.children[0].textContent).join(' / '));

// 대분류 > 소분류(방식) > 카드
const subsOf = (sec) => sec.children.filter((c) => c.classList.contains('sub'));
const cardsOf = (sub) => sub.children
  .find((c) => c.classList.contains('cards')).children.map((li) => li.children[0]);
const cards = sections.flatMap((sec) => subsOf(sec).flatMap(cardsOf));

const BANDS = ['그냥', '추론', '탐색', '중간'];
const FACES = { '그냥': '😒', '중간': '😐', '추론': '😎', '탐색': '🤮' };
const bandEl = (b) => b.children[0].children.find((c) => c.classList.contains('band'));
const cardBand = (b) => {
  const el = bandEl(b);
  return el ? el.getAttribute('data-band') : null;
};

{
  const subs = sections.flatMap(subsOf);
  check('소분류 = 방식별', subs.length > 0,
    sections.map((sec) => subsOf(sec).length + '개').join(' / '));
  // 소분류 제목은 방식 순서대로, 안에 든 카드는 모두 그 방식이어야 한다
  const order = ['그냥', '중간', '추론', '탐색'];
  const okOrder = sections.every((sec) => {
    const names = subsOf(sec).map((sub) => sub.children[0].children
      .find((c) => c.classList.contains('band')).getAttribute('data-band'));
    const rank = names.map((n) => order.indexOf(n));
    return rank.every((v, i) => v >= 0 && (i === 0 || rank[i - 1] < v));
  });
  check('소분류 순서', okOrder,
    sections.map((sec) => subsOf(sec).map((sub) => sub.children[0].children
      .find((c) => c.classList.contains('band')).getAttribute('data-band')).join('>')).join('  |  '));

  const pure = subs.every((sub) => {
    const want = sub.children[0].children
      .find((c) => c.classList.contains('band')).getAttribute('data-band');
    return cardsOf(sub).every((b) => cardBand(b) === want);
  });
  check('소분류 안은 같은 방식만', pure);

  const counts = subs.every((sub) => {
    const badge = sub.children[0].children.find((c) => c.classList.contains('count'));
    return badge && Number(badge.textContent) === cardsOf(sub).length;
  });
  check('소분류 개수 표시', counts);
}
check('퍼즐 카드', cards.length > 0, `${cards.length}개`);
check('진행 표시', /\d+ \/ \d+/.test(nodes.progress.textContent), nodes.progress.textContent);

{
  const done = cards.filter((b) => b.classList.contains('done'));
  check('클리어한 퍼즐 표시', done.length === 1, `${done.length}개`);
  // 숨기거나 잠그지 않는다. 다시 눌러 풀 수 있어야 한다
  check('클리어해도 다시 누를 수 있음',
    done.length === 1 && (done[0].handlers.click || []).length > 0);
}

const cardDiff = (b) => {
  const badge = b.children[1].children.find((c) => c.classList.contains('diff'));
  return badge ? Number(badge.textContent) : NaN;
};
check('카드마다 난이도', cards.every((b) => Number.isFinite(cardDiff(b))));
check('난이도 1~100', cards.every((b) => cardDiff(b) >= 1 && cardDiff(b) <= 100));

// 난이도는 소분류 칸 안에서만 오름차순이면 된다
const runs = sections.flatMap((sec) => subsOf(sec).map((sub) => cardsOf(sub).map(cardDiff)));
check('소분류 안 난이도 오름차순',
  runs.every((run) => run.every((d, i) => i === 0 || run[i - 1] <= d)),
  runs.map((r) => r.join(' ')).join('  |  '));

// .preview > .shape > .chip > i 까지 내려가 실제 점 격자를 확인한다
const chipDots = (previewEl) => previewEl.children
  .flatMap((shape) => shape.children.filter((c) => c.classList.contains('chip')))
  .map((chip) => chip.children.length);
check('카드에 모양 칩',
  cards.every((b) => chipDots(b.children[1].children[0]).every((n) => n > 0)));

{
  const used = new Set();
  const walk = (el) => {
    el.classList.set.forEach((c) => used.add(c));
    el.children.forEach(walk);
  };
  nodes.groups.children.forEach(walk);
  const clash = [...used].filter((c) => relocating.has(c));
  check('카드 클래스가 전역 배치 규칙과 안 겹침', clash.length === 0, clash.join(' ') || '없음');
}

const banded = cards.filter((b) => BANDS.includes(cardBand(b)));
check('카드마다 방식 뱃지', banded.length === cards.length, `${banded.length}/${cards.length}`);
{
  const tally = {};
  cards.forEach((b) => { const v = cardBand(b); tally[v] = (tally[v] || 0) + 1; });
  check('네 종류 다 나옴', BANDS.every((n) => tally[n] > 0),
    BANDS.map((n) => `${n} ${tally[n] || 0}`).join(' '));
  // 색을 따로 주므로 클래스도 붙어 있어야 한다
  check('뱃지 클래스', cards.every((b) => {
    const el = bandEl(b);
    return el && el.classList.contains('b-' + el.getAttribute('data-band'));
  }));
  check('뱃지가 이모티콘', cards.every((b) => {
    const el = bandEl(b);
    return el && el.textContent === FACES[el.getAttribute('data-band')];
  }), [...new Set(cards.map((b) => bandEl(b).textContent))].join(' '));
}

/* ── 퍼즐 열기 ── */

cards[0].dispatch('click', {});
check('퍼즐 열면 게임 화면', nodes.play.hidden === false && nodes.select.hidden === true,
  `play=${nodes.play.hidden} select=${nodes.select.hidden}`);
check('퍼즐 이름 표시', !!nodes['stage-name'].textContent, nodes['stage-name'].textContent);
check('상단 바에 난이도와 방식', nodes['stage-diff'].children.length === 2,
  nodes['stage-diff'].children.map((c) => c.textContent).join(' '));

const tiles = grid.children.filter((t) => t.classList.contains('tile'));
check('격자 100칸', tiles.length === 100, `${tiles.length}칸`);

const fieldTiles = tiles.filter((t) => t.classList.contains('field'));
check('활성 칸 있음', fieldTiles.length > 0, `${fieldTiles.length}칸`);

const dots = chipDots(nodes.preview);
check('모양 미리보기', dots.length > 0 && dots.every((n) => n > 0),
  `칩 ${dots.length}개, 점 ${dots.join('/')}`);
const rotLabels = nodes.preview.children
  .flatMap((shape) => shape.children.filter((c) => c.classList.contains('rot')));
check('회전 수 표시', rotLabels.length === dots.length && rotLabels.every((r) => /회전 [124]/.test(r.textContent)),
  rotLabels.map((r) => r.textContent).join(' '));

const d = nodes['outline-path'].getAttribute('d') || '';
check('필드 외곽선', d.startsWith('M') && d.length > 20, `${d.length}자`);

// 활성 칸 하나를 실제로 눌러 칠해지는지
const cell = 80;   // getBoundingClientRect 가 0,0 이고 칸은 80px 로 잡힌다
const at = (c, r) => ({ clientX: c * cell + cell / 2, clientY: r * cell + cell / 2 });
const press = (c, r, id = 1) => nodes.board.dispatch('pointerdown', {
  button: 0, pointerType: 'mouse', pointerId: id, ...at(c, r),
  target: { closest: () => null }, preventDefault() {},
});
const tileAt = (c, r) =>
  (c >= 0 && r >= 0 && c < 10 && r < 10) ? tiles[r * 10 + c] : null;
const isField = (c, r) => !!tileAt(c, r) && tileAt(c, r).classList.contains('field');

const first = tiles.findIndex((t) => t.classList.contains('field'));
press(first % 10, Math.floor(first / 10));
nodes.board.dispatch('pointerup', {});
check('클릭하면 칠해짐', !!tiles[first].style.backgroundColor,
  tiles[first].style.backgroundColor || '색 없음');

nodes.reset.dispatch('click', {});   // 판을 비우고 시작한다

/**
 * 목표 모양을 화면에서 읽어 온다. 칩은 pc x pr 격자에 점을 찍어 두었으므로
 * 켜진 점의 좌표가 곧 모양이다. 스테이지가 바뀌어도 검사가 따라간다.
 */
function shapeFromChip(previewEl) {
  const chip = previewEl.children[0].children.find((c) => c.classList.contains('chip'));
  const pc = Number(chip.style['--pc']);
  const out = [];
  chip.children.forEach((dot, i) => {
    if (dot.classList.contains('on')) out.push([i % pc, Math.floor(i / pc)]);
  });
  return out;
}

const shape = shapeFromChip(nodes.preview);

/** 모양이 통째로 활성 칸 위에 얹히는 자리 */
function findSpot(cells) {
  for (let r = 0; r < 10; r++) {
    for (let c = 0; c < 10; c++) {
      if (cells.every(([dc, dr]) => isField(c + dc, r + dr))) return [c, r];
    }
  }
  return null;
}

const spot = findSpot(shape);
if (!spot) {
  check('목표 모양 놓을 자리', false);
} else {
  const [oc, or_] = spot;
  const placed = shape.map(([dc, dr]) => [oc + dc, or_ + dr]);
  const key = ([c, r]) => c + ',' + r;
  const want = new Set(placed.map(key));

  /**
   * 한 색으로 이어 칠한다. 빈 칸을 누르면 새 색이 배정되므로, 첫 칸만 눌러
   * 색을 얻고 나머지는 이미 칠한 이웃에서 끌어와 같은 색을 잇는다.
   */
  function paintShape(cellsList, idBase) {
    const [fc, fr] = cellsList[0];
    press(fc, fr, idBase);
    nodes.board.dispatch('pointerup', {});
    const done = new Set([key(cellsList[0])]);
    let id = idBase;
    let progress = true;
    while (done.size < cellsList.length && progress) {
      progress = false;
      for (const [c, r] of cellsList) {
        if (done.has(key([c, r]))) continue;
        const near = [[c - 1, r], [c + 1, r], [c, r - 1], [c, r + 1]]
          .find((n) => done.has(key(n)));
        if (!near) continue;
        press(near[0], near[1], ++id);   // 칠해진 칸에서 시작하면 그 색이 이어진다
        nodes.board.dispatch('pointermove', at(c, r));
        nodes.board.dispatch('pointerup', {});
        done.add(key([c, r]));
        progress = true;
      }
    }
    return done.size === cellsList.length;
  }

  check('모양대로 칠하기', paintShape(placed, 10));

  const painted = tiles.filter((t) => t.style.backgroundColor).length;
  check('칠한 칸 수', painted === shape.length, `${painted}/${shape.length}칸`);

  const marked = placed.filter(([c, r]) => tileAt(c, r).classList.contains('match'));
  check('모양 일치하면 유리 질감', marked.length === shape.length,
    `${marked.length}/${shape.length}칸`);

  // 칠해진 칸을 홀드하면 그 색 전체가 지워져야 한다
  press(oc + shape[0][0], or_ + shape[0][1], 60);
  const marking = placed.filter(([c, r]) => tileAt(c, r).classList.contains('holding'));
  check('홀드 중 표시', marking.length === shape.length,
    `${marking.length}/${shape.length}칸`);

  runTimers();
  const left = placed.filter(([c, r]) => tileAt(c, r).style.backgroundColor);
  check('홀드하면 같은 색 전부 지워짐', left.length === 0, `${left.length}칸 남음`);

  nodes.board.dispatch('pointerup', {});
  check('홀드 표시 정리됨',
    tiles.filter((t) => t.classList.contains('holding')).length === 0);

  // 두 칸을 한 색으로 칠해 두고, 칸을 옮기면 홀드가 취소되는지
  const pair = placed.slice(0, 2);
  paintShape(pair, 70);
  press(pair[0][0], pair[0][1], 80);
  nodes.board.dispatch('pointermove', at(pair[1][0], pair[1][1]));
  runTimers();                                 // 옮겼으니 홀드는 안 터져야 한다
  const kept = pair.filter(([c, r]) => tileAt(c, r).style.backgroundColor);
  check('옮기면 홀드 취소', kept.length === 2, `${kept.length}/2칸 남음`);
  nodes.board.dispatch('pointerup', {});

  // 짧게 누르면 그 칸만 지워진다
  press(pair[0][0], pair[0][1], 90);
  nodes.board.dispatch('pointerup', {});
  check('짧게 누르면 한 칸만 지워짐',
    !tileAt(pair[0][0], pair[0][1]).style.backgroundColor
    && !!tileAt(pair[1][0], pair[1][1]).style.backgroundColor);
}

// 목록으로 돌아가기
nodes.back.dispatch('click', {});
check('뒤로 가면 목록', nodes.select.hidden === false && nodes.play.hidden === true);

// 두 종 스테이지를 열면 모양 칩이 둘 나와야 한다
const dualSec = nodes.groups.children.find((sec) => sec.children[0].textContent.includes('두 종'));
if (!dualSec) {
  check('두 종 묶음 있음', false);
} else {
  dualSec.children.filter((c) => c.classList.contains('sub'))[0]
    .children.find((c) => c.classList.contains('cards'))
    .children[0].children[0].dispatch('click', {});
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
