"""Resolve serialized-file dependencies; gameplay-selected bundles remain roots."""
from pathlib import PurePosixPath

_BUILTINS={'unity_builtin_extra','unity default resources','unity_builtin_extra.asset'}


def build_dependency_graph(records):
    owners={}
    for identifier,record in sorted(records.items()):
        for name in record['files']:
            key=PurePosixPath(name.replace('\\','/')).name
            previous=owners.get(key)
            if previous is not None:
                same=record.get('contentHash')
                if not same or same!=records[previous].get('contentHash'):
                    raise ValueError('Ambiguous serialized file identity: '+key)
            else: owners[key]=identifier
    graph={}
    for identifier,record in records.items():
        dependencies=set()
        for external in record['externals']:
            key=PurePosixPath(external.replace('\\','/')).name
            if key.lower() in _BUILTINS:continue
            owner=owners.get(key)
            if owner is None:raise ValueError('Unresolved external: '+external)
            if owner!=identifier and records[owner].get('contentHash')!=record.get('contentHash'):
                dependencies.add(owner)
            elif owner!=identifier and not record.get('contentHash'):
                dependencies.add(owner)
        graph[identifier]=sorted(dependencies)
    return graph


def inspect_sources(sources):
    """Offline only. UnityPy is not imported by the running HTTP service."""
    import hashlib
    import UnityPy
    records={}
    for identifier,path in sorted(sources.items()):
        data=path.read_bytes();env=UnityPy.load(data)
        files,externals=[],[]
        for asset in env.assets:
            files.append(asset.name)
            externals.extend(e.path for e in asset.externals)
        if not files:raise ValueError('No serialized files: '+identifier)
        records[identifier]={'files':files,'externals':externals,'contentHash':hashlib.sha256(data).hexdigest()}
    return build_dependency_graph(records)
