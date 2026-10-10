"""Check tracked source integrity and relative Markdown links, offline."""
from pathlib import Path
import hashlib
import json
import re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
manifest = json.loads((ROOT/'manifests/source-checksums.json').read_text(encoding='utf-8'))
for item in manifest['files']:
    path = ROOT/item['path']
    if not path.is_file():
        raise SystemExit(f'Missing source: {item["path"]}')
    data = path.read_bytes()
    if item['normalize_lf']:
        data = data.replace(b'\r\n', b'\n')
    if hashlib.sha256(data).hexdigest() != item['sha256']:
        raise SystemExit(f'Source SHA256 mismatch: {item["path"]}')
links = 0
for doc in [ROOT/'README.md', *sorted((ROOT/'docs').glob('*.md'))]:
    content = doc.read_text(encoding='utf-8')
    if 'C:\\Users\\' in content or 'C:/Users/' in content:
        raise SystemExit(f'Personal host path in {doc.relative_to(ROOT)}')
    # PowerShell casts such as [int](Get-Item ...) inside code are not links.
    prose = re.sub(r'(?ms)^```[^\n]*\n.*?^```[ \t]*(?:\n|$)', '', content)
    for match in re.finditer(r'\]\(([^)]+)\)', prose):
        target = match.group(1).split('#',1)[0]
        if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
            continue
        resolved = (doc.parent/unquote(target)).resolve()
        if not resolved.is_relative_to(ROOT) or not resolved.exists():
            raise SystemExit(f'Broken or external local link in {doc.relative_to(ROOT)}: {target}')
        links += 1
    if len(re.findall(r'^```',content,re.M)) % 2:
        raise SystemExit(f'Unclosed code block: {doc.relative_to(ROOT)}')
print(f'REPOSITORY CHECK PASSED: {len(manifest["files"])} source hashes, {links} local links. No device contacted.')
