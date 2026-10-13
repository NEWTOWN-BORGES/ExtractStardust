"""
EXTRACT: STARDUST — exporta as 5 naves V2 aprovadas na fase A para o jogo (FBX por nave, peças juntas por sistema).
  blender -b --factory-startup -P export_v2_game.py -- <pasta_tmp> <tmp.blend> <pasta_fbx>

Cada FBX tem: Body, Cockpit, Reactor, Cooling, Armor, Hover, Intake_R/L, Wings_R/L (pernas/asas), Propulsion_R/L(/C)
e Empties Socket_*. O nariz fica virado para -Y (frente do Blender) para o Unity o ler como +Z; chão em z=0.
"""
import os
import re
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
FBX_DIR = os.path.abspath(sys.argv[sys.argv.index('--') + 3])
os.makedirs(FBX_DIR, exist_ok=True)

SHIPS = [('strix', 'strix_v3.py', 'strix_y_arch'), ('wraith', 'wraith_v4.py', 'wraith_arch'), ('nomad', 'nomad_v4.py', 'nomad_m_arch'),
         ('bastion', 'bastion_v1.py', 'bastion_crab'), ('vortex', 'vortex_v1.py', 'vortex_intake')]

RULES = [   # (regex sobre o nome sem prefixo, sistema; '#' = acrescentar lado _R/_L)
    (r'^(Core_)', 'Propulsion_C'),                       # VORTEX: zona central de propulsão
    (r'(Prop_|Outer_|Foot_)', 'Propulsion#'),
    (r'(Intake|Duct)', 'Intake#'),
    (r'(Leg|Ski|Plate_|PlateF|PlateR|Shoulder|Fender|Arm_|Strut_|Endplate|KneeBeam|LowerBeam|KneeJoint|KneeEmitter|KneePlate)', 'Wings#'),
    (r'(Canopy|Seat|Hoop|Yoke|Dash|Strap|Visor|CockpitRail|WindDeflector|CageTopBar|Headrest|Bolster)', 'Cockpit'),
    (r'(Reactor|CoreGap)', 'Reactor'),
    (r'(Radiator|RadLouver|Coolant|HeatVent|VentFrame|Tank|PropCowl|CowlVent)', 'Cooling'),
    (r'(Armor|RamPlate|CrushBox|PropSkirt)', 'Armor'),
    (r'(Hover|CenterKeel|KeelPlate)', 'Hover'),
]
SIDE = re.compile(r'_(R|L)(?=_|$|\d)')


def system_of(name):
    base = name.split('_', 1)[1] if '_' in name else name
    for rx, sysname in RULES:
        if re.search(rx, base):
            if sysname.endswith('#'):
                m = SIDE.search(base) or SIDE.search(name)
                return sysname[:-1] + '_' + (m.group(1) if m else 'R')
            return sysname
    return 'Body'


def build_ship(script, fn):
    src = open(os.path.join(HERE, script), encoding='utf-8').read()
    src = re.sub(r'\n(if globals\(\)\.get\(\'RUN_V3\', True\):\n    )?main\(\)\s*$', '\n', src)
    g = {'__name__': 'v2_lib', '__file__': os.path.join(HERE, script), 'RUN_V3': False}
    exec(compile(src, script, 'exec'), g)
    coll = bpy.data.collections.new('Ship')
    g['SC'].collection.children.link(coll)
    g['COLL'] = coll
    g[fn]()
    return coll


def bake_and_join(coll):
    dg = bpy.context.evaluated_depsgraph_get()
    groups, empties = {}, []
    for ob in list(coll.objects):
        if ob.type == 'EMPTY':
            empties.append(ob)
            continue
        if ob.type != 'MESH':
            continue
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
        ob.modifiers.clear()
        ob.data = me
        groups.setdefault(system_of(ob.name), []).append(ob)
    for sysname, objs in groups.items():
        with bpy.context.temp_override(active_object=objs[0], object=objs[0], selected_objects=objs, selected_editable_objects=objs):
            bpy.ops.object.join()
        objs[0].name = objs[0].data.name = sysname
    for e in empties:   # sockets: 'Y1_Socket_Wing_R' -> 'Socket_Wing_R'
        i = e.name.find('Socket_')
        e.name = e.name[i:] if i >= 0 else e.name
    # nariz para -Y (frente do Blender) -> +Z no Unity
    for ob in coll.objects:
        ob.matrix_world = __import__('mathutils').Matrix.Rotation(3.14159265, 4, 'Z') @ ob.matrix_world
    return {k: len(v) for k, v in groups.items()}


for ship, script, fn in SHIPS:
    coll = build_ship(script, fn)
    counts = bake_and_join(coll)
    path = os.path.join(FBX_DIR, ship + '.fbx')
    bpy.ops.export_scene.fbx(filepath=path, use_selection=False, object_types={'MESH', 'EMPTY'}, apply_scale_options='FBX_SCALE_UNITS',
                             axis_forward='-Z', axis_up='Y', bake_space_transform=True, use_mesh_modifiers=True, mesh_smooth_type='FACE',
                             add_leaf_bones=False, bake_anim=False, path_mode='STRIP')
    tris = sum(len(p.vertices) - 2 for ob in coll.objects if ob.type == 'MESH' for p in ob.data.polygons)
    print(f"[V2 export] {ship}: {os.path.getsize(path) // 1024} KB, {tris} tris, sistemas={sorted(counts)}", flush=True)
