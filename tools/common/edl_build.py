"""Build the pinned edl-ng source and Q6A patch on the current host."""
from pathlib import Path
import platform
import shutil
import subprocess

from .files import ROOT, digest, load_json

DEPENDENCY = ROOT / 'tools/dependencies/edl-ng'


def host_runtime():
    systems = {'Windows': 'win', 'Linux': 'linux', 'Darwin': 'osx'}
    machines = {'AMD64': 'x64', 'x86_64': 'x64', 'aarch64': 'arm64', 'arm64': 'arm64', 'ARM64': 'arm64'}
    try:
        return systems[platform.system()] + '-' + machines[platform.machine()]
    except KeyError as exc:
        raise ValueError('Host OS or architecture is not supported by this build recipe') from exc


def build_plan(runtime):
    lock = load_json(DEPENDENCY / 'source.lock.json')
    if runtime not in lock['runtimes']:
        raise ValueError(f'Unsupported edl-ng runtime: {runtime}')
    patch = DEPENDENCY / 'q6a.patch'
    if digest(patch) != lock['patch_sha256']:
        raise ValueError('edl-ng patch differs from source.lock.json')
    source = ROOT / '.work/edl-ng' / runtime
    output = ROOT / 'artifacts/edl-ng' / runtime
    commands = [
        ['git', 'clone', '--no-checkout', lock['upstream'], str(source)],
        ['git', '-C', str(source), 'checkout', '--detach', lock['base_commit']],
        ['git', '-C', str(source), 'apply', '--check', str(patch)],
        ['git', '-C', str(source), 'apply', str(patch)],
        ['dotnet', 'test', str(source / 'QCEDL.NET.Tests/QCEDL.NET.Tests.csproj'), '-c', 'Release'],
        ['dotnet', 'publish', str(source / 'QCEDL.CLI/QCEDL.CLI.csproj'), '-c', 'Release',
         '-r', runtime, '--self-contained', 'true', '-o', str(output)],
    ]
    return {'runtime': runtime, 'base_commit': lock['base_commit'], 'commands': commands,
            'source': str(source), 'output': str(output), 'device_contacted': False}


def build(runtime):
    plan = build_plan(runtime)
    if runtime != host_runtime():
        raise ValueError('Native AOT recipe builds for the current OS and architecture only')
    if Path(plan['source']).exists() or Path(plan['output']).exists():
        raise ValueError('Build directory already exists; preserve previous sources and outputs')
    for executable in ['git', 'dotnet']:
        if not shutil.which(executable):
            raise ValueError(f'Required build tool is missing: {executable}')
    Path(plan['source']).parent.mkdir(parents=True, exist_ok=True)
    for command in plan['commands']:
        subprocess.run(command, check=True)
    return plan
