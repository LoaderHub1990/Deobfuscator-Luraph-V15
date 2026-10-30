#!/usr/bin/env python3
"""Fetch Lua scripts and follow supported chained payload delivery URLs."""
import argparse, os, re, sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

USER_AGENTS = ['Roblox/WinInet', 'okhttp/3.10.0', 'ExploitExecutor', 'Synapse', 'Krnl']

def request(url, headers=None, data=None, timeout=20):
    h = {'User-Agent': USER_AGENTS[0], 'Accept': '*/*', 'Accept-Language': 'en-US,en;q=0.9', 'Connection': 'close'}
    h.update(headers or {})
    req = Request(url, data=data, headers=h, method='POST' if data is not None else 'GET')
    with urlopen(req, timeout=timeout) as r:
        body = r.read().decode('latin-1')
        return r.status, dict(r.headers.items()), body

def fetch_bypass(url):
    last = None
    for ua in USER_AGENTS:
        try:
            status, headers, body = request(url, {'User-Agent': ua}, timeout=15)
            ctype = headers.get('Content-Type', '')
            if 'text/html' in ctype.lower() and '<!doctype' in body.lower() and not url.endswith('.html'):
                continue
            if status == 200 and body: return status, headers, body
        except Exception as e: last = e
    if last: raise last
    return request(url, timeout=15)

def main():
    ap = argparse.ArgumentParser(description='Fetch a Lua script URL')
    ap.add_argument('url'); ap.add_argument('-o', '--output')
    a = ap.parse_args()
    print(f'[*] Fetching: {a.url}')
    status, headers, body = fetch_bypass(a.url)
    if status != 200: raise SystemExit(f'[!] Server responded with status {status}')
    print(f'[+] Received {len(body)} bytes (Content-Type: {headers.get("Content-Type", "")})')
    delivery = re.search(r'https://api\.jnkie\.com/api/v1/luascripts/delivery/[^\s"\']+', body)
    if delivery:
        keyvar = re.search(r'getgenv\(\)\.SCRIPT_KEY\s+or\s+([A-Za-z_][A-Za-z0-9_]*)', body)
        key = os.getenv(keyvar.group(1), '') if keyvar else os.getenv('JNKIE_KEY', '')
        key = key or os.getenv('JNKIE_KEY', '')
        print(f'[*] JNKIE delivery chain detected (key {"provided" if key else "empty"})')
        st, _, payload_url = request(delivery.group(0), data=key.encode(), headers={'Content-Type':'text/plain'})
        if st != 200 or not payload_url.strip().startswith('https://cdn.jnkie.com/'):
            raise SystemExit('[!] Delivery denied or unexpected response')
        print(f'[*] Following CDN payload: {payload_url.strip()}')
        st, headers, body = fetch_bypass(payload_url.strip())
        if st != 200 or len(body) < 100: raise SystemExit('[!] CDN fetch failed')
        print(f'[+] Luraph payload received: {len(body)} bytes')
    out = Path(a.output) if a.output else Path(__file__).parent / 'output' / (Path(urlparse(a.url).path).name or 'fetched_script.lua')
    if out.suffix.lower() != '.lua' and not a.output: out = out.with_suffix('.lua')
    out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(body.encode('latin-1'))
    print(f'[+] Successfully saved to: {out}')

if __name__ == '__main__': main()
