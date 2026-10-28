"""Project configuration. Relative paths are always relative to this project root."""
import json
import pathlib
import os
ROOT = pathlib.Path(__file__).resolve().parents[1]

def load_config(filename=None):
    source=pathlib.Path(filename or ROOT/'rtd.config.json').resolve()
    data=json.loads(source.read_text(encoding='utf-8-sig'))
    data['_root']=source.parent
    for section in ('api','resources'):
        if section in data:
            port=data[section].get('port')
            if isinstance(port,bool) or not isinstance(port,int) or not 1<=port<=65535:
                raise ValueError(section+' port must be an integer from 1 to 65535')
    return data

SETTINGS=load_config()
def path_for(name, settings=None):
    settings=SETTINGS if settings is None else settings
    value=pathlib.Path(settings['paths'][name])
    return value if value.is_absolute() else settings['_root']/value

STARTERS = [((20000, 5), (11112, 5), (10033, 2)),
            ((20010, 5), (11133, 5), (10000, 2)),
            ((20020, 5), (11102, 5), (10030, 2)),
            ((20030, 5), (11100, 5), (10021, 2))]


