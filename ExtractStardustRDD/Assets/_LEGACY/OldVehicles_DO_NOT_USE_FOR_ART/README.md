# LEGACY — NÃO USAR PARA ARTE

As naves atuais são protótipos anteriores à Vehicle Construction & Art Bible v1.1. Ficam no jogo **só para testar física e gameplay** enquanto as naves V2 são feitas do zero.

Visual legado (gerado por código, sem ficheiros de mesh):
- `Assets/RedDust/Runtime/Presentation/PlaceholderCraft.cs` (nave e mota provisórias)
- `Assets/RedDust/Runtime/Game/ShipBuilder.cs` → `BuildVisual` (naves modulares provisórias)
- `Art/Blender/rdd_render_ships.py` e as fotos em `Docs/fotos/naves` e `Docs/fotos/hangar`

Regras:
- Não modificar estes visuais para fazer as V2.
- Não decalcar as silhuetas nem reaproveitar proporções, asas, motores, aletas, blindagem, cockpits ou materiais.
- Não usar como referência de concept art.
- Podem ser consultados apenas para requisitos técnicos: envelope do collider (`CraftTuning.hullSize`), sockets (`Catalog`), ligação à física e scripts.

As V2 vivem em `Assets/ExtractStardust/Vehicles/V2/` (fonte Blender em `Art/Vehicles_V2/`).
