"""Immutable bundle publication and snapshot resolution; no request-time hashing."""
import contextlib
import hashlib
import json
import os
import re
from pathlib import Path, PurePosixPath
import tempfile
import fcntl

_RESOURCE_ID_CHARS = re.compile(r'[A-Za-z0-9/_.-]+')


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()


def _digest(value):
    return hashlib.sha256(_encoded(value)).hexdigest()


def _atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.pending-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data); stream.flush(); os.fsync(stream.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        with contextlib.suppress(FileNotFoundError): os.unlink(temporary)


def _validate_id(identifier):
    if (not isinstance(identifier, str) or not identifier or len(identifier)>256
            or identifier.startswith('/') or '\\' in identifier
            or any(p in ('', '.', '..') for p in identifier.split('/'))
            or _RESOURCE_ID_CHARS.fullmatch(identifier) is None
            or not identifier.endswith('.unity3d')):
        raise ValueError('Invalid resource id')


def _closure(resources, roots):
    visiting, done = set(), set()
    def visit(identifier, depth):
        if depth > 128: raise ValueError('Dependency depth exceeded')
        if identifier in visiting: raise ValueError('Dependency cycle')
        if identifier in done: return
        if identifier not in resources: raise ValueError('Unknown resource: '+identifier)
        visiting.add(identifier)
        for dependency in resources[identifier]['dependencies']: visit(dependency, depth+1)
        visiting.remove(identifier); done.add(identifier)
    for identifier in roots: visit(identifier, 0)
    return [resources[key] for key in sorted(done)]


def load_snapshot(output):
    snapshot = json.loads((Path(output)/'active.json').read_bytes())
    if snapshot.get('protocol') != 1: raise ValueError('Unsupported catalog')
    return snapshot


def publish_resources(sources, dependencies, output, *, required_prefabs=None):
    """Publish under a process lock; active.json is the release visibility point."""
    output = Path(output); output.mkdir(parents=True, exist_ok=True)
    with (output/'.publish.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _publish_locked(sources, dependencies, output, required_prefabs or {})


def _publish_locked(sources, dependencies, output, required_prefabs):
    if not sources: raise ValueError('Empty release')
    if set(dependencies)-set(sources): raise ValueError('Unknown dependency owner')
    if set(required_prefabs)-set(sources): raise ValueError('Unknown prefab contract owner')
    resources = {}
    for identifier in sorted(sources):
        _validate_id(identifier)
        deps = dependencies.get(identifier, [])
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps):
            raise ValueError('Invalid dependencies')
        prefabs=required_prefabs.get(identifier, [])
        if (not isinstance(prefabs,list) or len(prefabs)>256 or any(not isinstance(name,str) or not 0<len(name)<=256 or any(ord(c)<32 or ord(c)==127 for c in name) for name in prefabs)):
            raise ValueError('Invalid prefab export contract')
        resources[identifier] = {'id':identifier, 'dependencies': sorted(set(deps)), 'requiredPrefabs':sorted(set(prefabs))}
    _closure(resources, list(resources))
    registry_path = output/'versions.json'
    registry = json.loads(registry_path.read_bytes()) if registry_path.exists() else {'next':1000000000,'versions':{}}
    for identifier, entry in resources.items():
        data = Path(sources[identifier]).read_bytes()
        if not data: raise ValueError('Empty resource: '+identifier)
        digest = hashlib.sha256(data).hexdigest()
        name = PurePosixPath(identifier).name
        key = identifier+'@'+digest
        if key not in registry['versions']:
            if registry['next'] > 2147483647: raise ValueError('Cache version exhausted')
            registry['versions'][key] = registry['next']; registry['next'] += 1
        relative = Path('blobs')/digest/name
        target = output/relative
        if target.exists():
            if hashlib.sha256(target.read_bytes()).hexdigest()!=digest: raise ValueError('Corrupt published blob')
        else: _atomic(target, data)
        entry.update(sha256=digest, size=len(data), cacheVersion=registry['versions'][key],
                     downloadPath='/resources/v1/'+relative.as_posix())
    _atomic(registry_path, _encoded(registry))
    snapshot = {'protocol':1, 'resources':resources}
    snapshot['snapshotId'] = _digest(snapshot)
    encoded = _encoded(snapshot)
    _atomic(output/'snapshots'/(snapshot['snapshotId']+'.json'), encoded)
    _atomic(output/'active.json', encoded)
    return snapshot['snapshotId']


def resolve_snapshot(snapshot, roots):
    if not isinstance(roots,list) or not roots or len(roots)>4096:
        raise ValueError('Invalid roots')
    for identifier in roots: _validate_id(identifier)
    resources = _closure(snapshot['resources'], roots)
    return {'protocol':1, 'snapshotId':snapshot['snapshotId'],
            'closureDigest':_digest(resources), 'resources':resources}
