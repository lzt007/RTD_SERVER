"""Export inferred Shingetsu records separately; never overwrite an existing export."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from rtd.masters.catalog import load_catalog
from rtd.masters.shingetsu import build_candidate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    masters, levels = load_catalog()
    candidate = build_candidate(masters, levels)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'candidate.json').write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    preview = ['INFERRED maps, not recovered originals. . empty / 1-4 wolf slot / R rare / B boss / E exit / S start']
    for level in candidate['levels']:
        preview.append('\nQuest '+str(level['level_data_id']))
        cells = bytes.fromhex(level['map_data'])
        width = level['width']
        for y in range(level['height']):
            row = []
            for x in range(width):
                cell = cells[y*width+x]
                symbol = {0:'.',17:'R',160:'B',192:'E'}.get(cell,str(cell))
                if (x,y)==(level['start_x'],level['start_y']):
                    symbol='S'
                row.append(symbol)
            preview.append(''.join(row))
    (args.output / 'maps.txt').write_text('\n'.join(preview)+'\n', encoding='utf-8')
    print(str(args.output))


if __name__ == '__main__':
    main()
