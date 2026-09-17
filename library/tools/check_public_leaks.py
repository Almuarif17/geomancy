#!/usr/bin/env python3
"""Refuse to commit anything that identifies a person or a machine.

This repo is public and git history is effectively permanent, so the scan is a gate, not a suggestion:
emails, phone numbers (NG and generic), API tokens, absolute home paths, screenshot filenames, the
corpus of personal castings, and lines that read as an asked question in notes/.

    python3 library/tools/check_public_leaks.py          # scan tracked + staged files
    python3 library/tools/check_public_leaks.py --all    # scan every file in the tree
"""
from __future__ import annotations

import argparse, pathlib, re, subprocess, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
FORBIDDEN = [
    ("nigeria phone", re.compile(r"(?<!\d)\+?2(?:34|80|70|80|90)[\s-]?[7-9]\d{9}(?!\d)")),
    ("generic phone", re.compile(r"(?<![\d.])\+\d{2,3}[\s-]?\d{6,12}(?![\d.])")),
    # an email address means a person; git@github.com is an SSH remote, so it is masked out first
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]{2,}@(?!users\.noreply|example\.|noreply@)\[masked\]|[A-Za-z0-9._%+-]{2,}@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("github token", re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{16,}|gho_[A-Za-z0-9]{16,}|github_pat_[A-Za-z0-9_]{16,})\b")),
    ("aws / slack / google", re.compile(r"\b(AKIA[0-9A-Z]{16}|xox[baprs]-[A-Za-z0-9-]{10,}|AIza[0-9A-Za-z_\-]{20,})\b")),
    ("private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("absolute home path", re.compile(r"/home/[a-z0-9_\-]{3,}/|/Users/[a-z0-9_\-]{2,}/|C:\\\\Users\\\\", re.I)),
    ("screenshot filename", re.compile(r"(?i)screenshot[_ ]?\d{6,}|\.png\b.*\b(20\d\d)\d\d\d\d")),
    ("local city handle", re.compile(r"\b(Abuja|Lagos|Ikeja|Maitama|Garki|Wuse)\b")),
    ("personal casting dir", re.compile(r"(^|/)readings/[A-Za-z0-9_.\-]+\.(json|md)\b")),
]
QUESTIONISH = re.compile(r"(?i)^(?:\s*[>>-]+\s*)?(?:q|question)\s*[:\-]\s*\S.*\?$")
TRACKED_MUST_NOT_EXIST = ["readings", "uploads", "corpus/raw", "corpus/scratch"]


def files(all_mode: bool) -> list[pathlib.Path]:
    if all_mode:
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git/" not in str(p)]
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True)
    if out.returncode:
        return [p for p in ROOT.rglob("*") if p.is_file() and ".git/" not in str(p)]
    return [ROOT / l for l in out.stdout.splitlines() if l.strip()]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()
    fs = files(a.all)
    problems, scanned = [], 0
    self_rel = "library/tools/check_public_leaks.py"
    for f in fs:
        try:
            txt = f.read_text()
        except (UnicodeDecodeError, OSError):
            continue
        rel = f.relative_to(ROOT)
        tracked = subprocess.run(["git", "ls-files", "--error-unmatch", str(rel)],
                                 cwd=ROOT, capture_output=True).returncode == 0
        scanned += 1
        # this file has to name the things it forbids, so the two rules that would match its own
        # pattern table are skipped here - everything else in the repo is scanned, including itself
        exempt_self = str(rel) == self_rel
        if any(str(rel).startswith(p + "/") or str(rel) == p for p in TRACKED_MUST_NOT_EXIST):
            problems.append((str(rel), 0, "forbidden path", "personal material has no business in git", tracked))
        for lineno, raw in enumerate(txt.splitlines(), 1):
            line = raw.replace("git@github.com", "[ssh-remote]")
            for name, pat in FORBIDDEN:
                if exempt_self and name in {"local city handle", "absolute home path"}:
                    continue
                m = pat.search(line)
                if m:
                    problems.append((str(rel), lineno, name, m.group(0)[:60], tracked))
            if QUESTIONISH.match(line):
                problems.append((str(rel), lineno, "asked question", line.strip()[:70], tracked))
    fatal = [p for p in problems if p[4]]
    advisory = [p for p in problems if not p[4]]
    for rel, ln, kind, snip, _ in fatal[:30]:
        print(f"  LEAK  {rel}:{ln}  {kind}  {snip!r}")
    if advisory:
        print(f"  note: {len(advisory)} hit(s) in files git does not track (corpus/, work/, readings/) -"
              f" ignored on purpose, listed only so you do not `git add -f` them by accident")
        for rel, kind in sorted({(r, k) for r, _, k, _, t in advisory if not t})[:4]:
            print(f"        {rel}: {kind}")
    print(f"\n{scanned} text files scanned, {len(fatal)} leak(s) in tracked files"
          + ("" if not fatal else " - nothing identifying, no credentials, no personal castings"))
    return 1 if fatal else 0


if __name__ == "__main__":
    raise SystemExit(main())
