# The arcade style switch (player, 2026-10-27: "uma versão gráfica tipo Rocket League"): /Game/World/MPC_Style, scalar
# Stylize: 0 photoreal (the default), 1 arcade (clean, saturated, readable surfaces). The game sets it with
# -EXStyle=Arcade (AEXGameMode::ApplyStyle). Exec'd by make_ground_material.py, make_rock_material.py and
# make_ship_materials.py after their own expr() helper: style_input() is the material input for their Custom nodes.
import unreal

MPC_PATH = "/Game/World/MPC_Style"
if unreal.EditorAssetLibrary.does_asset_exist(MPC_PATH):
    STYLE_MPC = unreal.EditorAssetLibrary.load_asset(MPC_PATH)
else:
    STYLE_MPC = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        "MPC_Style", "/Game/World", unreal.MaterialParameterCollection, unreal.MaterialParameterCollectionFactoryNew())
    _p = unreal.CollectionScalarParameter()
    _p.set_editor_property("parameter_name", "Stylize")
    _p.set_editor_property("default_value", 0.0)
    STYLE_MPC.set_editor_property("scalar_parameters", [_p])
    unreal.EditorAssetLibrary.save_asset(MPC_PATH)


def style_input():
    return expr(unreal.MaterialExpressionCollectionParameter, collection=STYLE_MPC, parameter_name="Stylize")  # noqa: F821
