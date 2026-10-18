# Bakes the project's own seamless desert textures with Blender (no third-party art).
# Usage: blender -b -P bake_desert_textures.py -- <output_dir> [size]
# Every pattern is sampled on a 4D torus (cos/sin of U and V), so all textures tile perfectly.
import bpy
import math
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
OUT = argv[0]
SIZE = int(argv[1]) if len(argv) > 1 else 2048
TAU = 2.0 * math.pi
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 4
scene.render.bake.margin = 0
scene.render.bake.normal_g = 'NEG_Y'  # Unreal uses DirectX-style normal maps
bpy.ops.mesh.primitive_plane_add(size=2.0)
plane = bpy.context.active_object


class Graph:
    def __init__(self, name):
        self.mat = bpy.data.materials.new(name)
        self.mat.use_nodes = True
        self.nodes = self.mat.node_tree.nodes
        self.links = self.mat.node_tree.links
        self.nodes.clear()
        self.out = self.nodes.new("ShaderNodeOutputMaterial")
        coords = self.nodes.new("ShaderNodeTexCoord")
        sep = self.nodes.new("ShaderNodeSeparateXYZ")
        self.links.new(coords.outputs["UV"], sep.inputs[0])
        self.u = sep.outputs[0]
        self.v = sep.outputs[1]
        self.cu = self.op("COSINE", self.op("MULTIPLY", self.u, TAU))
        self.su = self.op("SINE", self.op("MULTIPLY", self.u, TAU))
        self.cv = self.op("COSINE", self.op("MULTIPLY", self.v, TAU))
        self.sv = self.op("SINE", self.op("MULTIPLY", self.v, TAU))

    def link(self, src, dst):
        if isinstance(src, (int, float)):
            dst.default_value = src
        else:
            self.links.new(src, dst)

    def op(self, operation, a, b=None):
        n = self.nodes.new("ShaderNodeMath")
        n.operation = operation
        self.link(a, n.inputs[0])
        if b is not None:
            self.link(b, n.inputs[1])
        return n.outputs[0]

    def mix(self, a, b, t):
        return self.op("ADD", a, self.op("MULTIPLY", self.op("SUBTRACT", b, a), t))

    def torus(self, ru, rv):
        comb = self.nodes.new("ShaderNodeCombineXYZ")
        self.link(self.op("MULTIPLY", self.cu, ru), comb.inputs[0])
        self.link(self.op("MULTIPLY", self.su, ru), comb.inputs[1])
        self.link(self.op("MULTIPLY", self.cv, rv), comb.inputs[2])
        return comb.outputs[0], self.op("MULTIPLY", self.sv, rv)

    def noise(self, ru, rv, scale, detail=4.0, rough=0.55, seed=0.0):
        vec, w = self.torus(ru, rv)
        n = self.nodes.new("ShaderNodeTexNoise")
        n.noise_dimensions = '4D'
        self.link(vec, n.inputs["Vector"])
        self.link(self.op("ADD", w, seed), n.inputs["W"])
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = detail
        n.inputs["Roughness"].default_value = rough
        return n.outputs["Fac"]

    def cracks(self, r, scale, seed=0.0):
        vec, w = self.torus(r, r)
        n = self.nodes.new("ShaderNodeTexVoronoi")
        n.voronoi_dimensions = '4D'
        n.feature = 'DISTANCE_TO_EDGE'
        self.link(vec, n.inputs["Vector"])
        self.link(self.op("ADD", w, seed), n.inputs["W"])
        n.inputs["Scale"].default_value = scale
        return n.outputs["Distance"]

    def cracks_aniso(self, ru, rv, scale, seed=0.0):
        vec, w = self.torus(ru, rv)
        n = self.nodes.new("ShaderNodeTexVoronoi")
        n.voronoi_dimensions = '4D'
        n.feature = 'DISTANCE_TO_EDGE'
        self.link(vec, n.inputs["Vector"])
        self.link(self.op("ADD", w, seed), n.inputs["W"])
        n.inputs["Scale"].default_value = scale
        return n.outputs["Distance"]

    def ramp(self, factor, stops):
        n = self.nodes.new("ShaderNodeValToRGB")
        elements = n.color_ramp.elements
        while len(elements) < len(stops):
            elements.new(0.5)
        for element, (position, color) in zip(elements, stops):
            element.position = position
            element.color = (color[0], color[1], color[2], 1.0)
        self.link(factor, n.inputs["Fac"])
        return n.outputs["Color"]


def bake(graph, color, height, name, bump_strength, bump_distance):
    plane.data.materials.clear()
    plane.data.materials.append(graph.mat)
    image_node = graph.nodes.new("ShaderNodeTexImage")
    graph.nodes.active = image_node
    for kind, colorspace in (("D", "sRGB"), ("N", "Non-Color")):
        image = bpy.data.images.new(name + "_" + kind, SIZE, SIZE, alpha=False)
        image.colorspace_settings.name = colorspace
        image_node.image = image
        for l in list(graph.out.inputs["Surface"].links):
            graph.links.remove(l)
        if kind == "D":
            emission = graph.nodes.new("ShaderNodeEmission")
            graph.link(color, emission.inputs["Color"])
            graph.link(emission.outputs[0], graph.out.inputs["Surface"])
            bpy.ops.object.bake(type='EMIT')
        else:
            bump = graph.nodes.new("ShaderNodeBump")
            bump.inputs["Strength"].default_value = bump_strength
            bump.inputs["Distance"].default_value = bump_distance
            graph.link(height, bump.inputs["Height"])
            bsdf = graph.nodes.new("ShaderNodeBsdfPrincipled")
            graph.link(bump.outputs["Normal"], bsdf.inputs["Normal"])
            graph.link(bsdf.outputs[0], graph.out.inputs["Surface"])
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT')
        image.filepath_raw = os.path.join(OUT, "T_%s_%s.png" % (name, kind))
        image.file_format = 'PNG'
        image.save()
        print("BAKED", image.filepath_raw)


# --- Sand: pink-orange Wadi Rum sand with wind ripples (tile = 4 m, ~30 ripples) and fine grain. ---
g = Graph("Sand")
low = g.noise(1.0, 1.0, 1.6, 3.0, 0.5, 3.0)
mid = g.noise(1.0, 1.0, 6.0, 4.0, 0.55, 7.0)
grain = g.noise(1.0, 1.0, 90.0, 2.0, 0.6, 11.0)
phase = g.op("ADD", g.op("MULTIPLY", g.v, 30.0 * TAU), g.op("MULTIPLY", g.op("SUBTRACT", mid, 0.5), 9.0))
ripple = g.op("ADD", 0.5, g.op("MULTIPLY", g.op("SINE", g.op("ADD", phase, g.op("MULTIPLY", g.op("SINE", phase), 0.45))), 0.5))
ripple_mask = g.op("POWER", g.op("MULTIPLY", g.op("ADD", low, 0.15), 1.25), 1.5)  # ripples fade in and out
factor = g.op("ADD", g.op("ADD", g.op("MULTIPLY", low, 0.55), g.op("MULTIPLY", grain, 0.3)), g.op("MULTIPLY", ripple, 0.12))
color = g.ramp(factor, [(0.25, (0.52, 0.20, 0.10)), (0.55, (0.68, 0.30, 0.16)), (0.85, (0.80, 0.42, 0.25))])
height = g.op("ADD", g.op("MULTIPLY", g.op("MULTIPLY", ripple, ripple_mask), 0.7), g.op("MULTIPLY", grain, 0.15))
bake(g, color, height, "Sand", 0.45, 0.02)

# --- Sandstone: thin horizontal strata, dark vertical "desert varnish" streaks, rounded erosion and a few
# sparse fractures (tile = 6 m; V maps to world height on cliffs). ---
g = Graph("Rock")
blotch = g.noise(1.0, 1.0, 2.0, 6.0, 0.62, 2.0)
warp = g.op("MULTIPLY", g.op("SUBTRACT", g.noise(1.0, 1.0, 3.0, 3.0, 0.5, 31.0), 0.5), 9.0)
strata = g.op("ADD", 0.5, g.op("MULTIPLY", g.op("SINE", g.op("ADD", g.op("MULTIPLY", g.v, 7.0 * TAU), warp)), 0.5))
thin = g.op("POWER", g.op("ADD", 0.5, g.op("MULTIPLY", g.op("SINE", g.op("ADD", g.op("MULTIPLY", g.v, 23.0 * TAU),
    g.op("MULTIPLY", warp, 1.7))), 0.5)), 8.0)
varnish = g.op("POWER", g.noise(6.0, 0.25, 4.0, 5.0, 0.55, 5.0), 1.6)  # long dark vertical streaks
erosion = g.noise(1.0, 1.0, 14.0, 6.0, 0.6, 17.0)
# Vertical columnar joints: Voronoi cells stretched along V, so most fractures run up the cliff.
joints = g.op("SUBTRACT", 1.0, g.op("MINIMUM", g.op("MULTIPLY", g.cracks_aniso(3.0, 0.6, 1.4, 4.0), 30.0), 1.0))
fracture_mask = g.op("GREATER_THAN", g.noise(1.0, 1.0, 1.5, 2.0, 0.5, 41.0), 0.62)
fracture = g.op("MULTIPLY", g.op("SUBTRACT", 1.0, g.op("MINIMUM", g.op("MULTIPLY", g.cracks(1.0, 1.8, 4.0), 40.0), 1.0)), fracture_mask)
fine = g.noise(1.0, 1.0, 70.0, 3.0, 0.6, 13.0)
factor = g.op("ADD", g.op("MULTIPLY", blotch, 0.45), g.op("MULTIPLY", strata, 0.1))
factor = g.op("SUBTRACT", factor, g.op("MULTIPLY", thin, 0.06))
factor = g.op("SUBTRACT", factor, g.op("MULTIPLY", varnish, 0.4))
factor = g.op("ADD", factor, g.op("ADD", g.op("MULTIPLY", erosion, 0.14), g.op("MULTIPLY", fine, 0.1)))
factor = g.op("SUBTRACT", factor, g.op("ADD", g.op("MULTIPLY", joints, 0.25), g.op("MULTIPLY", fracture, 0.15)))
color = g.ramp(factor, [(0.05, (0.05, 0.018, 0.014)), (0.3, (0.16, 0.05, 0.035)), (0.55, (0.30, 0.11, 0.06)), (0.8, (0.48, 0.24, 0.14))])
height = g.op("ADD", g.op("MULTIPLY", blotch, 0.45), g.op("MULTIPLY", strata, 0.15))
height = g.op("SUBTRACT", height, g.op("MULTIPLY", thin, 0.08))
height = g.op("ADD", height, g.op("MULTIPLY", erosion, 0.35))
height = g.op("SUBTRACT", height, g.op("ADD", g.op("MULTIPLY", joints, 0.45), g.op("MULTIPLY", fracture, 0.3)))
height = g.op("ADD", height, g.op("MULTIPLY", fine, 0.12))
bake(g, color, height, "Rock", 0.7, 0.05)

# --- Macro variation: very low frequency tint/brightness noise used across hundreds of metres. ---
g = Graph("Macro")
macro = g.noise(1.0, 1.0, 1.2, 6.0, 0.55, 21.0)
color = g.ramp(macro, [(0.2, (0.0, 0.0, 0.0)), (0.8, (1.0, 1.0, 1.0))])
bake(g, color, macro, "Macro", 0.1, 0.1)
print("BAKE DONE")
