import unreal

asset_path = "/Game/World/M_World"
material = unreal.EditorAssetLibrary.load_asset(asset_path)
if not material:
    raise RuntimeError("Missing world material: " + asset_path)

expected_texture = "/Game/World/T_WorldTrack.T_WorldTrack"
expected_sampler = unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_GRAYSCALE
changed = 0
for expression in unreal.MaterialEditingLibrary.get_material_expressions(material):
    if not isinstance(expression, unreal.MaterialExpressionTextureSample):
        continue
    texture = expression.get_editor_property("texture")
    if texture and texture.get_path_name() == expected_texture:
        old_sampler = expression.get_editor_property("sampler_type")
        if old_sampler != expected_sampler:
            expression.set_editor_property("sampler_type", expected_sampler)
            changed += 1
            unreal.log("WORLD_TRACK_SAMPLER fixed expression=%s old=%s new=%s" %
                       (expression.get_name(), old_sampler, expected_sampler))

if changed == 0:
    raise RuntimeError("No T_WorldTrack texture sample needed repair in M_World")
unreal.MaterialEditingLibrary.recompile_material(material)
if not unreal.EditorAssetLibrary.save_asset(asset_path):
    raise RuntimeError("Could not save repaired world material")
unreal.log("WORLD_TRACK_SAMPLER saved M_World; changed_samples=%d" % changed)
