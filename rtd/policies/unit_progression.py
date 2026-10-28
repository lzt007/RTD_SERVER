"""Original ordinary-compose arithmetic; normal success is local policy."""
import math
import struct


def single(value):
    return struct.unpack('<f',struct.pack('<f',value))[0]


def level_exp(master, level):
    powers=(2.380000114440918,2.4200000762939453,2.4800000190734863,
            2.5799999237060547,2.6600000858306885,2.5999999046325684)
    return int(single((level-1)**powers[master['category']-1]*single(master['grow'])))


def material_exp(unit, master):
    if unit['unit_id']==50000:
        return unit['exp']
    return int(single(single(master['mix'])*single(math.pow(single(unit['level']),0.5))))


def evo_points(level, set_pt):
    return int(single(single(single(level-1)*single(math.sqrt(set_pt)))+single(set_pt)))


def compose_result(base, materials, masters):
    master=masters[base['unit_id']]
    add=sum(material_exp(u,masters[u['unit_id']]) for u in materials)
    exp=min(level_exp(master,master['lv_max']),base['exp']+add)
    level=base['level']
    while level<master['lv_max'] and exp>=level_exp(master,level+1):
        level+=1
    return dict(price=base['level']*master['cost']*len(materials),
                add_exp=add,level=level,exp=exp)
