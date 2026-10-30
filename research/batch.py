#!/usr/bin/env python3
"""Run a directory of Lua samples through the Python CLI in sequence."""
import argparse, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder', type=Path)
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--budget', type=int, default=300)
    ap.add_argument('--devirt-rounds', type=int, default=2)
    ap.add_argument('--output', type=Path, default=ROOT / 'research' / 'output')
    a = ap.parse_args()
    files = sorted(p for p in a.folder.glob('*') if p.is_file() and p.suffix.lower() in {'.lua','.luau','.txt'})
    a.output.mkdir(parents=True, exist_ok=True)
    failures = 0
    for source in files:
        target = a.output / (source.stem + '.deobf.luau')
        cmd = [sys.executable, str(ROOT/'deob.py'), str(source), '--timeout', str(a.timeout),
               '--budget', str(a.budget), '--devirt-rounds', str(a.devirt_rounds), '-o', str(target)]
        print('\n[batch] ' + source.name, flush=True)
        result = subprocess.run(cmd, cwd=ROOT)
        failures += result.returncode != 0
    print(f'\n[batch] complete: {len(files)-failures} succeeded, {failures} failed')
    return 1 if failures else 0

if __name__ == '__main__':
    raise SystemExit(main())
