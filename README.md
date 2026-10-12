# EXTRACT: STARDUST

**RACE. SURVIVE. EXTRACT.** Corrida de extração com naves antigravidade (Unity 6 URP + Blender), PC e Android.

| Pasta | O que é | Estado |
|---|---|---|
| `ExtractStardustRDD/` | **Projeto principal.** Expedição RED DUST DIVIDE: canyon natural (Utah/Arizona reinterpretado), física antigravidade nova a 400–450 km/h, geologia modelada no Blender. | Milestone 1 (laboratório de física) validado: 18/18 testes. A seguir: M2 (blockout da RED DUST DIVIDE). |
| `ExtractStardust/` | Protótipo anterior: ilha de 24 km em mundo aberto (porte do RACESTARS), com expedição, circuitos, Wi-Fi e tela dividida. | Arquivo/teste. |

## Projeto principal (ExtractStardustRDD)

- Plano e decisões: `ExtractStardustRDD/Docs/RDD_00_Plano_Vertical_Slice.md`
- Relatório de validação da física: `ExtractStardustRDD/Docs/M1_Relatorio_Fisica.md`
- Pipeline da geologia: `Art/Courses/*.json` (percurso por segmentos) → Blender `Art/Blender/rdd_build_course.py` → FBX + dados do percurso → Unity (`Red Dust` no menu do editor).

### Gerar a geologia e abrir o projeto

A geometria gerada (FBX de dezenas de MB) não vai para o repositório: gera-se em ~2 minutos.

```powershell
# requisitos: Unity 6000.3.26f1 (com Android Build Support), Blender 5.2
powershell -ExecutionPolicy Bypass -File ExtractStardustRDD/Tools/m1_pipeline.ps1 -Build
```

O script corre o Blender (geologia), importa no Unity (com teste automático de eixos/escala do FBX), valida a física (`Docs/M1_Relatorio_Fisica.md`) e compila `Builds/Windows/RedDustDivide.exe`.

### Controlos

| Ação | Comando PS4/PS5 | Teclado |
|---|---|---|
| Direção | analógico esquerdo | A / D |
| Boost | R2 ou X | W / Shift |
| Travão / derrapagem (com direção) | L2 ou Quadrado | S / Espaço |
| Reposicionar | Triângulo | R |
| Olhar à volta / para trás | analógico direito / R3 | C |
| Pausa | OPTIONS | Esc |
