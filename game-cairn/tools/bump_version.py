"""버전 올리기 — VERSION · play.html · index.html · docs/버전.md 를 한 번에.

    python tools/bump_version.py 0.15.0 "한 줄 요약"

커밋 제목은 `cairn v0.15.0: …` 로.
"""
import datetime
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    if len(sys.argv) < 3 or not re.fullmatch(r"\d+\.\d+\.\d+", sys.argv[1]):
        raise SystemExit(__doc__)
    v, note = sys.argv[1], sys.argv[2]
    (ROOT / "VERSION").write_text(v + "\n", encoding="utf-8")
    for name, pat, rep in (
        ("play.html", r"const APP_VERSION = '[\d.]+';", f"const APP_VERSION = '{v}';"),
        ("index.html", r'<span class="ver">v[\d.]+</span>', f'<span class="ver">v{v}</span>'),
    ):
        p = ROOT / name
        t = p.read_text(encoding="utf-8")
        t2, n = re.subn(pat, rep, t)
        if n != 1:
            raise SystemExit(f"{name}: 버전 자리를 못 찾음 ({n})")
        p.write_text(t2, encoding="utf-8")
    log = ROOT / "docs" / "버전.md"
    t = log.read_text(encoding="utf-8")
    row = f"| {v} | {datetime.date.today()} | {note} | |\n"
    t = t.replace("|---|---|---|---|\n", "|---|---|---|---|\n" + row, 1)
    log.write_text(t, encoding="utf-8")
    print("버전", v)


if __name__ == "__main__":
    main()
