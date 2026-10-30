#!/usr/bin/env python3
"""Python entry point for the Luraph deobfuscator."""
from __future__ import annotations
import argparse, os, re, sys, tempfile
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

ROOT = Path(__file__).resolve().parent
CORE = ROOT / 'core'
sys.path.insert(0, str(CORE))
from obfuscators.base import Job
from obfuscators.luraph_v15 import LuraphV15, restore_header_newline
from obfuscators.luraph_v15 import driver as v15_driver

SUPPORTED = {'.lua', '.luau', '.txt'}

class LuraphV14(LuraphV15):
    name = 'luraph_v14'
    label = 'Luraph v14'
    def detect(self, source: str) -> float:
        head = source[:600]
        m = re.search(r'This file was protected using Luraph Obfuscator v(\d+)', head, re.I)
        if m:
            return 1.0 if m.group(1) == '14' else 0.0
        sample = source[:200000]
        if ('LPH' in sample and ('repeat\n' in sample or 'until false' in sample)
                and ('loadstring' in sample or 'setmetatable' in sample)):
            return 0.45
        return 0.0

PLUGINS = [LuraphV15(), LuraphV14()]

def detect(source: str):
    scored = [(p.detect(source), p) for p in PLUGINS]
    confidence, plugin = max(scored, key=lambda x: x[0])
    if confidence <= 0:
        plugin = LuraphV15()
    return plugin, confidence

def parse_args(argv=None):
    ap = argparse.ArgumentParser(description='Python Luraph deobfuscator')
    ap.add_argument('inputs', nargs='+', help='Lua/Luau files or folders')
    ap.add_argument('-o', '--output')
    ap.add_argument('--detect', action='store_true')
    ap.add_argument('--no-devirt', dest='no_devirt', action='store_true')
    ap.add_argument('--no-hooks', dest='no_hooks', action='store_true')
    ap.add_argument('--no-fold', dest='no_fold', action='store_true')
    ap.add_argument('--debug', action='store_true')
    ap.add_argument('--strings', action='store_true')
    ap.add_argument('--keep-harness', action='store_true')
    ap.add_argument('--keep-preamble', action='store_true')
    ap.add_argument('--timeout', type=int, default=90)
    ap.add_argument('--budget', type=int, default=30)
    ap.add_argument('--jobs', type=int, default=1)
    ap.add_argument('--max-runs', type=int, default=12)
    ap.add_argument('--devirt-rounds', type=int, default=200)
    ap.add_argument('--executor', default='Wave')
    ap.add_argument('--input-text')
    ap.add_argument('--studio', action='store_true')
    ap.add_argument('--port', type=int, default=27019)
    ap.add_argument('--studio-wait', type=int, default=300)
    ap.add_argument('--cfg', action='append', default=[])
    ap.add_argument('--raw')
    return ap.parse_args(argv)

def collect_files(paths):
    found, seen = [], set()
    for raw in paths:
        p = Path(raw).expanduser().resolve()
        if not p.exists():
            print(f'[!] path not found, skipping: {raw}', file=sys.stderr); continue
        candidates = sorted(x for x in p.iterdir() if x.is_file()) if p.is_dir() else [p]
        for item in candidates:
            if item.is_file() and item.suffix.lower() in SUPPORTED and str(item) not in seen:
                seen.add(str(item)); found.append(item)
            elif item.is_file() and p.is_file() and item.suffix.lower() not in SUPPORTED:
                print(f'[!] unsupported extension: {item}', file=sys.stderr)
    return found

def process_file(path: Path, args):
    source = path.read_bytes().decode('latin-1')
    plugin, confidence = detect(source)
    if args.detect:
        print(f'{path.name}\t{plugin.name}\t{confidence:.2f}\t{plugin.label}')
        return str(path)
    print(f'[*] obfuscator: {plugin.label} (detected, {confidence:.2f})', file=sys.stderr)
    outdir = path.parent / 'output'
    outdir.mkdir(parents=True, exist_ok=True)
    trace_name = re.sub(r'(\.luau?|\.txt)?$', '.deobf.luau', path.name, flags=re.I)
    work = None if args.debug else tempfile.mkdtemp(prefix='deob_python_')
    trace_path = Path(args.output).resolve() if args.debug and args.output else (outdir / trace_name if args.debug else Path(work) / trace_name)
    final = Path(args.output).resolve() if args.output and len(args.inputs) == 1 else outdir / path.name
    final.parent.mkdir(parents=True, exist_ok=True)
    try:
        fixed = restore_header_newline(source)
        source_path = path
        if fixed != source:
            print('[*] header comment ran into the code: split it', file=sys.stderr)
            source = fixed
            source_path = (Path(work) if work else outdir) / (path.name + '.src.lua')
            source_path.write_bytes(source.encode('latin-1'))
        job = Job(str(path), source, args, str(trace_path), args.debug, plugin.label)
        job.source_path = str(source_path)
        # The Python engine is the actual implementation; no JS runtime is involved.
        result = v15_driver.run(job)
        if result and Path(result).exists():
            content = Path(result).read_text(encoding='utf-8', errors='replace')
            content = re.sub(r'^(\s*--(?:[ \t]*(?:Deobfuscated by|Detected obfuscation|Local names are inferred|source:|NOTE: reconstructed|during the trace)[^\n]*\n?|\s*\n))+', '', content)
            final.write_text(content, encoding='utf-8', newline='\n')
            print(f'[+] result: {final}', file=sys.stderr)
            return str(final)
        print(f'[!] no result for {path.name}', file=sys.stderr)
        return None
    finally:
        if work:
            import shutil; shutil.rmtree(work, ignore_errors=True)

def main():
    args = parse_args()
    files = collect_files(args.inputs)
    if not files:
        print('[!] no valid .lua / .luau / .txt input files found', file=sys.stderr); return 1
    if args.detect:
        for p in files:
            src = p.read_bytes().decode('latin-1'); plugin, conf = detect(src)
            print(f'{p.name}\t{plugin.name}\t{conf:.2f}\t{plugin.label}')
        return 0
    if args.output and len(files) > 1:
        print('[!] --output ignored for multiple inputs', file=sys.stderr)
    ok = bad = 0
    workers = max(1, min(args.jobs, len(files)))
    if workers == 1:
        for p in files:
            print(f'\n[*] processing {p}', file=sys.stderr)
            try:
                if process_file(p, args): ok += 1
                else: bad += 1
            except Exception as e:
                bad += 1; print(f'[!] failed on {p.name}: {e}', file=sys.stderr)
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            jobs = {pool.submit(process_file, p, args): p for p in files}
            for future in as_completed(jobs):
                try: ok += bool(future.result())
                except Exception as e: bad += 1; print(f'[!] failed on {jobs[future].name}: {e}', file=sys.stderr)
    print(f'\n[*] done: {ok} succeeded, {bad} failed out of {len(files)}', file=sys.stderr)
    return 1 if bad and not ok else 0

if __name__ == '__main__':
    raise SystemExit(main())
