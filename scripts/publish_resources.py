"""Publish an explicit resource/recursive-dependency manifest without changing originals.

Manifest: {"resources": {"id.unity3d": {"source": "relative/file", "dependencies": []}}}
Source paths are relative to the manifest. Every entry must declare dependencies.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from rtd.resource_catalog import publish_resources


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('manifest',type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    resources=json.loads(args.manifest.read_text())['resources']
    sources, dependencies={},{}
    for identifier,entry in resources.items():
        sources[identifier]=args.manifest.parent/entry['source']
        dependencies[identifier]=entry['dependencies']
    print(publish_resources(sources,dependencies,args.output))


if __name__=='__main__': main()
