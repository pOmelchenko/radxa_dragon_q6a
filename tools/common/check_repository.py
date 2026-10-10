"""Validate documentation and pinned external artifacts, without board access."""
import re
from urllib.parse import unquote

from .files import ROOT, check_entries, digest, load_json


def main():
    vendor = ROOT / 'docs/vendor'
    sources = load_json(vendor / 'sources.json')
    originals = [{'path': item['file'], 'bytes': item['bytes'], 'sha256': item['sha256']}
                 for item in sources['files']]
    check_entries(vendor, originals)
    sums = {line.split()[1]: line.split()[0]
            for line in (vendor / 'SHA256SUMS').read_text(encoding='utf-8').splitlines() if line.strip()}
    if sums != {item['path']: item['sha256'] for item in originals}:
        raise ValueError('Vendor SHA256SUMS differs from sources.json')
    dependency = ROOT / 'tools/dependencies/edl-ng'
    lock = load_json(dependency / 'source.lock.json')
    for key, filename in [('patch_sha256', 'q6a.patch'), ('license_sha256', 'LICENSE')]:
        if digest(dependency / filename) != lock[key]:
            raise ValueError(f'Pinned edl-ng artifact differs: {filename}')
    if not re.fullmatch('[0-9a-f]{40}', lock['base_commit']):
        raise ValueError('edl-ng source must be pinned to a complete commit hash')
    links = 0
    documents = [ROOT / 'README.md']
    for directory in ['docs', 'firmware', 'tools']:
        documents.extend(sorted((ROOT / directory).rglob('*.md')))
        for path in (ROOT / directory).rglob('*.json'):
            load_json(path)
    for doc in documents:
        content = doc.read_text(encoding='utf-8')
        if 'C:\\Users\\' in content or 'C:/Users/' in content:
            raise ValueError(f'Personal host path in {doc.relative_to(ROOT)}')
        prose = re.sub(r'(?ms)^```[^\n]*\n.*?^```[ \t]*(?:\n|$)', '', content)
        for match in re.finditer(r'\]\(([^)]+)\)', prose):
            target = match.group(1).split('#', 1)[0]
            if not target or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target):
                continue
            resolved = (doc.parent / unquote(target)).resolve()
            if not resolved.is_relative_to(ROOT) or not resolved.exists():
                raise ValueError(f'Broken local link in {doc.relative_to(ROOT)}: {target}')
            links += 1
        if len(re.findall(r'^```', content, re.M)) % 2:
            raise ValueError(f'Unclosed code block: {doc.relative_to(ROOT)}')
    print(f'REPOSITORY CHECK PASSED: {len(documents)} documents, {links} local links, '
          f'{len(originals)} vendor files and pinned edl-ng artifacts. No device contacted.')
