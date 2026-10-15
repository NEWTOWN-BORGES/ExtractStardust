"""Entrada legada segura; use os importadores limitados por categoria."""
import unreal

unreal.log_warning(
    "Este importador geral foi desativado para evitar reconstruir FBX densos e mapas com todas as pecas na origem. "
    "Use Import_Course_Batch.py para pistas e Import_Secondary_Assets.py para props, texturas, UI e audio."
)