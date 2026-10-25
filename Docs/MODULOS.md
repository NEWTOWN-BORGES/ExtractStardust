# Módulos, raridades, caixas e consumíveis (2026-10-25)

Os módulos são os do jogo antigo, a demo Unity das 5 naves antigas, adaptados às naves novas.
- **Regras:** GDD, documentos 02 (Naves e Equipamentos) e 03 (Itens, Consumíveis e Economia), em
  `ExtractStardustRDD/Docs/referencias/` no ramo `main`.
- **Código Unity de referência:** `ExtractStardustRDD/Assets/RedDust/Runtime/Meta/` (`Catalog.cs`, `Items.cs`,
  `Economy.cs`), também no `main`.

Os números são TARGETS DE TUNING, como nos documentos.

## 1. Naves e slots (Doc 02, secção 4)

| Nave | Classe | Vel | Ace | Man | Est | Casco | Efi | Ref | Boost | Passiva |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STRIX | M | 72 | 74 | 76 | 75 | 66 | 66 | 68 | 70 | ADAPTIVE TRIM |
| WRAITH | S/M | 82 | 80 | 90 | 58 | 46 | 57 | 60 | 78 | RAZOR LINE |
| NOMAD | M/L | 65 | 63 | 62 | 77 | 76 | 92 | 84 | 60 | LONG HAUL |
| BASTION | L | 61 | 54 | 52 | 92 | 96 | 65 | 73 | 55 | INERTIAL ANCHOR |
| VORTEX | M | 75 | 91 | 68 | 65 | 61 | 49 | 55 | 96 | OVERDRIVE RECOVERY |

**Slots** (com a classe aceite em cada um; "qualquer" aceita S, M e L):

| Nave | Motor | Propulsão | Asas | Cauda | Blindagem | Reator | Refrigeração | Utilidade | Slots extra |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| STRIX | M | M | próprias | M | M | M | M | qualquer | — |
| WRAITH | S/M | S | próprias | S | S | S/M | S | qualquer | — |
| NOMAD | M/L | M | próprias | M/L | M | M/L | L | qualquer | Aux (utilidade) |
| VORTEX | M | S/M | próprias | M | S/M | M | M | qualquer | Propulsão central S/M |
| BASTION | L | L | — | L | L | L | L | qualquer | Blindagem 2 (L) |

## 2. Famílias: o que se vê na nave

| Família | Por fora? | Onde (pontos de encaixe das naves novas) | No hangar, ao escolher |
| --- | --- | --- | --- |
| Asas | sim | `Socket_Wing_L/R`; substituem as asas de série | a asa aparece montada |
| Blindagem | sim | kit de carroçaria na pintura da nave: saias no fundo do casco, lâmina à volta do nariz e, nos kits pesados, aletas debaixo da cauda; sempre abaixo da cintura (longe do cockpit) e por baixo das asas | o kit aparece montado |
| Refrigeração | sim | `Socket_Cooling`: grelhas laterais ou radiadores no dorso | os radiadores aparecem |
| Cauda | sim | `Socket_Tail`: barbatanas atrás (por baixo na WRAITH, que já tem barbatanas em cima) | aparecem |
| Utilidade | não (por dentro) | no nariz, à frente do cockpit (na WRAITH, no nariz da cápsula: as longarinas levam as condutas de ar) | esqueleto, com o módulo a brilhar a ciano |
| Motor | não (por dentro) | nos motores de plasma | vista em **esqueleto**, com o motor ligado e as **chamas** do motor escolhido |
| Propulsão | não | os bocais | esqueleto, com as chamas do boost |
| Reator | não | o núcleo do reator | esqueleto, com o reator a brilhar na cor do módulo |

**Vista em esqueleto:** a carroçaria desaparece e fica o chassis com motores, reator, cockpit, longarinas e o módulo
de utilidade, como nos renders `*_inside.jpg` das naves.

**Blindagem = kit de carroçaria** (pedido do jogador, 2026-10-25): faz parte da nave, muda-lhe um pouco as linhas e
continua aerodinâmica. Nada de placas cinzentas nem de peças a sair do casco. As peças têm as cores da própria nave
(cor principal, friso na cor de destaque, rebordo na cor escura), as pontas são afiladas e nunca passam da cintura nem
chegam ao vidro.

## 3. Catálogo

### 3.1 Universais (26, do jogo antigo)

**Motores (por dentro; cada um tem a sua chama):**

| Id | Nome | Fabricante | Classe | Massa (kg) | Chama | Ênfase |
| --- | --- | --- | --- | --- | --- | --- |
| eng_vk4 | APEX VK-4 Sprint | APEX Dynamics | M | 0 | jato azul de núcleo branco | velocidade |
| eng_longstride | Meridian Longstride | Meridian Engineering | M | +20 | cone curto ciano | eficiência |
| eng_hx | Vanta HX Burner | Vanta Works | S | −10 | scramjet laranja com diamantes de choque | aceleração |
| eng_razor | APEX Razor-S | APEX Dynamics | S | −20 | jato fino violeta | velocidade e aceleração |
| eng_ironcore | Frontier Ironcore | Frontier Systems | L | +70 | chama larga laranja | aceleração |
| eng_relic | Oryx Relic Drive | Oryx Reclamation | L | +40 | feixe fino azul-branco | velocidade e eficiência |

**Propulsão (por dentro; mudam o boost):**

| Id | Nome | Fabricante | Classe | Massa (kg) | Ênfase |
| --- | --- | --- | --- | --- | --- |
| prop_twin | APEX Twin Jets | APEX Dynamics | S | −5 | boost |
| prop_vector | Meridian Vector M | Meridian Engineering | M | +15 | aceleração |
| prop_heavy | Frontier Heavy Thrust | Frontier Systems | L | +60 | boost e aceleração |

**Blindagem (por fora, kit de carroçaria):**

| Id | Nome | Fabricante | Classe | Massa (kg) | Visual |
| --- | --- | --- | --- | --- | --- |
| arm_skin | APEX Light Skin | APEX Dynamics | S | +30 | `armor_light`: saias finas (3,6 cm) com friso de destaque, lâmina pequena no nariz |
| arm_guard | Meridian Guard Plates | Meridian Engineering | M | +90 | `armor_guard`: saias em 3 painéis (6 cm), friso largo, lâmina, 2 aletas atrás |
| arm_plate | Frontier Bulwark | Frontier Systems | L | +180 | `armor_bulwark`: saias grossas (10 cm) com faixa escura de borracha, lâmina grande, aletas |
| arm_shell | Oryx Shell Lattice | Oryx Reclamation | M | +70 | `armor_shell`: carapaça arredondada com nervuras e junta a brilhar a ciano |

**Reatores (por dentro; cor do brilho):**

| Id | Nome | Fabricante | Classe | Massa (kg) | Cor |
| --- | --- | --- | --- | --- | --- |
| rea_spark | APEX Spark Core | APEX Dynamics | S | 0 | ciano |
| rea_steady | Meridian Steady Core | Meridian Engineering | M | +20 | azul |
| rea_flux | Vanta Flux Reactor | Vanta Works | M | +15 | magenta |
| rea_titan | Frontier Titan Core | Frontier Systems | L | +60 | âmbar |

**Refrigeração (por fora):**

| Id | Nome | Fabricante | Classe | Massa (kg) | Visual |
| --- | --- | --- | --- | --- | --- |
| cool_vent | APEX Vent Kit | APEX Dynamics | S | +10 | `cooling_vents` |
| cool_radiator | Meridian Radiator Array | Meridian Engineering | M | +35 | `cooling_radiator` |
| cool_grid | Frontier Heat Grid | Frontier Systems | L | +70 | `cooling_grid` |

**Caudas (por fora):**

| Id | Nome | Fabricante | Classe | Massa (kg) | Visual |
| --- | --- | --- | --- | --- | --- |
| tail_compact | APEX Compact Tail | APEX Dynamics | S | 0 | `tail_compact` |
| tail_twin | Meridian Twin Tail | Meridian Engineering | M | +20 | `tail_twin` |
| tail_long | Frontier Long Keel | Frontier Systems | L | +40 | `tail_keel` |

**Utilidade (por dentro, no nariz; só se vê no esqueleto):**

| Id | Nome | Fabricante | Classe | Massa (kg) | Visual |
| --- | --- | --- | --- | --- | --- |
| util_scanner | Meridian Scanner Mast | Meridian Engineering | M | +8 | `utility_mast`: radar de prato virado para a frente, sobre a caixa da eletrónica |
| util_routeintel | Oryx Route Oracle | Oryx Reclamation | M | +5 | `utility_dome`: núcleo a brilhar num giroscópio, sobre um bloco com alhetas |
| util_drone | Frontier Field Drone | Frontier Systems | M | +15 | `utility_drone`: drone dobrado no compartimento de lançamento, com a escotilha por cima |

### 3.2 Asas próprias de cada nave (12)

Cada nave tem três asas, desenhadas a partir da asa de série dela. A raiz é a mesma da asa de série (passa pelas
mesmas ranhuras da carroçaria) e a parte de fora muda.

| Nave | Asas |
| --- | --- |
| STRIX | Blade (curta e enflechada, com barbatana na ponta), Longspan (longa, com placas na ponta), Vector (segunda superfície por cima) |
| WRAITH | Blade, Vector, Glide (ponta dobrada para cima, bordo de ataque luminoso) |
| NOMAD | Longspan, Brace (grossa, com escora até ao casco), Glide |
| VORTEX | Blade, Vector, Glide |
| BASTION | as asas entram quando a nave nova estiver feita |

**Ênfase** de cada tipo de asa (como no jogo antigo, todas podem dar manobra e estabilidade, até +9 cada; o tipo
decide para onde vai a maior parte do budget):
- Blade: manobra.
- Longspan e Brace: estabilidade.
- Vector e Glide: as duas.

Ids no código: `wing_<tipo>_<nave>` (por exemplo `wing_glide_wraith`), com o fabricante do tipo no jogo antigo (Blade
APEX, Longspan Meridian, Vector Vanta, Brace Frontier, Glide Oryx).

### 3.3 Lendários (3)

Têm rolls controlados, perk e número de série, que se mantêm quando mudam de dono pelo espólio:

| Nome | Família | Efeito | Custo | Visual |
| --- | --- | --- | --- | --- |
| HELIOS V-9 | reator | energia +17%, boost +11%, refrigeração +8 | combustível +6% | brilho dourado claro |
| REDLINE-X | motor | acima de 90% da velocidade máxima, +3% de velocidade | calor do boost +15% | chama vermelha de núcleo branco, com faíscas |
| AEGIS FRAME | blindagem | dano de impacto −25% (na prática, choques mais fortes antes de perder vida) | massa +120 kg | kit largo, que abre em baixo, com banda de destaque entre frisos dourados, junta incandescente, lâmina maior e aletas |

## 4. Raridades e rolls (Doc 02, secção 7)

| Raridade | Cor | Budget de stats | Valor médio (STARDUST) |
| --- | --- | --- | --- |
| Comum | branco | 10 | 500 |
| Incomum | verde | 13 | 1 100 |
| Raro | azul | 16 | 3 000 |
| Épico | roxo | 20 | 7 000 |
| Lendário | dourado | 23 + perk | 18 000 ou mais |

- **Como se distribui o budget:** cada instância reparte-o pelos stats que a família permite, com um teto por item.
  Exemplos: motor até +9 de velocidade e +8 de aceleração; blindagem até +14 de casco.
- **Penalizações:** nas raridades altas pode sair uma penalização que devolve budget. Exemplos: motor com −eficiência
  ou −refrigeração; blindagem com −aceleração.
- **Instâncias diferentes:** duas peças com o mesmo nome podem ter rolls diferentes.
- **Raridade e chamas:**
  - raros: chama mais longa e mais brilhante;
  - épicos: diamantes de choque e faíscas;
  - lendários: chama própria.

## 5. Stats na corrida

Os módulos mexem na condução afinada pelo jogador ponto a ponto, contando só o que somam ao stat da própria nave
(`AEXHoverCraft::ApplyShipStats`). Os stats ficam entre 0 e 100.

| Stat | No jogo |
| --- | --- |
| Velocidade | velocidade máxima: +0,57% por ponto |
| Aceleração | força do motor: +0,6% por ponto; a massa dos módulos tira um pouco (raiz da massa da nave sobre a massa total) |
| Manobra | viragem: +0,5% por ponto |
| Estabilidade | aderência lateral: +0,5% por ponto |
| Casco | **vidas**: as da nave (VORTEX 2 … BASTION 5), mais 1 por cada 10 pontos de casco acima do da nave (máximo 6). Também aguenta choques +0,6% mais fortes por ponto antes de perder vida |
| Eficiência | consumo de combustível (secção 6) |
| Refrigeração | arrefecimento: 4 + 0,08 × refrigeração por segundo |
| Nitro (boost) | duração do nitro +0,6% e força +0,4% por ponto |
| Reparação | o Repair Foam e o Rapid Nanogel reparam 3% mais depressa e com menos perda de velocidade por ponto |
| Sensores | por agora só aparece no hangar (os avisos de perigo ficam para depois) |

## 6. Combustível e calor (novos, para os consumíveis e os stats terem efeito)

**Combustível:**
- Gasta-se por km: 236,9 / (eficiência + 123) % por km a fundo, menos com pouco acelerador (35% em ponto morto) e o
  dobro com nitro.
- Com isto a NOMAD gasta ~65% numa expedição de 59 km e a VORTEX ~80% (passa dos 90% se abusar do nitro).
- Sem combustível, a nave fica com metade da velocidade máxima.

**Calor:**
- Sobe 14 por segundo com o nitro (15% mais com o REDLINE-X) e baixa com a refrigeração quando o nitro está desligado.
- A 100 sobreaquece: fica sem nitro até baixar a 40, e com −10% de velocidade.

O HUD da corrida mostra as duas barras.

## 7. Consumíveis (Doc 03, secção 6): 4 slots

| Id | Nome | Preço | Efeito |
| --- | --- | --- | --- |
| coolant | Coolant Cell | 80 | −45 de calor |
| foam | Repair Foam | 100 | +1 vida em 8 s; −10% de velocidade enquanto repara |
| fuel | Fuel Cell | 120 | +30% de combustível |
| stab | Stabilizer Shot | 140 | 8 s de aderência e estabilidade extra |
| surge | Surge Cell | 180 | +70% de nitro na hora; +12 de calor |
| nanogel | Rapid Nanogel | 220 | +1 vida em 2,5 s; −25% de velocidade enquanto repara |

- **Slots:** 4, cada um com um consumível e até 2 unidades. Usam-se com **as teclas 1, 2, 3 e 4** e, no comando, com
  **as setas cima, baixo, esquerda e direita** (por esta ordem). Um consumível que não faria nada nesse momento
  (Coolant sem calor, reparação com as vidas cheias) não se gasta.
- **Stock e carga:** os consumíveis comprados ficam no stock, que está seguro. Os que se levam saem do stock.
  - Quem extrai recupera os que não gastou.
  - Quem é destruído perde a carga.

## 8. Loja e caixas (Doc 03, secções 7 e 8)

**Caixas:** 10 itens cada (4 a 6 componentes, o resto consumíveis). Nunca trazem naves.

| Caixa | Preço | Probabilidades e garantias |
| --- | --- | --- |
| STANDARD | 2 500 | 70% comum, 27% incomum, 3% raro |
| ADVANCED | 6 000 | 20% comum, 50% incomum, 27% raro, 3% épico; mínimo 1 raro |
| ELITE | 10 000 | 25% incomum, 55% raro, 20% épico; 1 épico garantido, mínimo 4 raros ou melhor, e **uma** tentativa de 4% por caixa de subir um item a lendário |

O ELITE custa 10 000 na demo; o documento prevê 13 500 no jogo final.

**Loja de componentes:**

| Raridade | Preço |
| --- | --- |
| Comum | 450–650 |
| Incomum | 900–1 300 |
| Raro | 2 400–3 500 |

Épicos e lendários não se vendem na loja. A oferta muda depois de cada expedição.

**Venda e cofre:**
- Vender dá 25% do valor.
- As caixas compradas vão para o **Cofre** e abrem-se lá, uma carta de cada vez, com a cor da raridade.

**Perfil novo:** 3 000 STARDUST, uma STANDARD CACHE no cofre e os consumíveis do jogo antigo (2 Repair Foam,
1 Fuel Cell, 1 Coolant Cell).

## 9. Fim da expedição: perdas e espólio com peças reais

- **Prémio por posição** (Doc 03, secção 3):

  | Posição | 1.º | 2.º | 3.º | … | 20.º |
  | --- | --- | --- | --- | --- | --- |
  | STARDUST | 1 600 | 1 300 | 1 100 | … | 225 |

  Multiplica-se por 0,70 (expedição de 10 a 15 min), e soma 250 por EXTRACTED. A **primeira extração** dá mais 500,
  uma vez só.
- **Perdas:** quem é destruído perde até 3 módulos montados, sorteados pelo valor. O módulo **segurado** (um por
  expedição) nunca se perde. Os consumíveis levados perdem-se todos.
- **Espólio:** junta as peças reais perdidas, incluindo as dos bots, que levam módulos reais. Reparte-se pelos
  EXTRACTED em serpentina por valor: o 1.º leva a mais valiosa, o 2.º a seguinte, e na volta seguinte a ordem
  inverte-se.

## 10. Hangar

Separadores (Q/E ou os gatilhos de ombro): **NAVE**, **EQUIPAR**, **CONSUMÍVEIS**, **LOJA** e **COFRE**. Maquetas:
`equip_wing.png`, `equip_engine.png`, `consumiveis.png`, `cofre.png` e `hud.png` (enviadas ao jogador a 2026-10-25).
- **NAVE:** W/S escolhem a nave; Enter lança a expedição.
- **EQUIPAR:**
  - à esquerda, os slots da nave com o módulo montado e a cor da raridade;
  - à direita, as peças compatíveis que tens (A/D passam por elas);
  - a nave mostra a peça em que estás: asas, blindagem (o kit), refrigeração e cauda por fora; para motor, reator,
    propulsão e utilidade, a vista em esqueleto, com o motor ligado e as chamas dele (o reator brilha na cor do
    módulo, o utilitário a ciano);
  - em baixo, as barras de stats, com o atual e o candidato, e as vidas;
  - Enter monta a peça, Backspace (X/Quadrado) volta à peça de série, T (Y/Triângulo) segura a peça do slot.
- **CONSUMÍVEIS:** os 4 slots: A/D mudam a quantidade (0 a 2; se faltar no stock, compra uma), Enter troca o
  consumível, Backspace esvazia.
- **LOJA:** as 3 caixas e os componentes em rotação; Enter compra. Uma peça que serve na nave aparece montada nela.
- **COFRE:** Enter abre uma caixa (as 10 cartas viram uma a uma; Enter mostra todas, Esc fecha) ou vende uma peça
  (Enter duas vezes, por 25% do valor).

## 11. Do Blender ao Unreal

- **`Scripts/ship_modules.py`** corre no fim de cada `build_<nave>.py` e escreve em `<saída>/modules/`:
  - `<nave>_core` (a nave sem asas), `<nave>_wing_stock` e `<nave>_skeleton`;
  - as 3 asas próprias e as peças universais ajustadas à carroçaria da nave (encontrada por raios): o kit de
    carroçaria segue o fundo do casco, foge das asas e nunca passa da cintura; o utilitário vai para o maior espaço
    livre dentro do nariz, à frente do cockpit, sem tocar na estrutura nem nos sistemas (o log diz `UTILITY BAY`);
  - `<nave>_modules.json`, com as peças e os bocais dos motores, para as chamas.

  Tudo fica no referencial da nave: no Unreal, cada peça vai em cima da malha da nave sem deslocamento.
- **`Scripts/render_modules.py`** faz as imagens de cada módulo na oficina.
- **As peças das 4 naves** estão em `SourceArt/TestShips/modules/` (84 ficheiros, 14 MB). Para as refazer:
  `python3 Scripts/build_<nave>.py <pasta> --no-render` e copiar `<pasta>/modules/` para lá.
- **No Unreal:** as peças importam-se para `/Game/Ships/<NAVE>/SM_<NAVE>_<PEÇA>` com
  `Scripts/import_ship_modules.py` (o `casa_tudo.ps1` já o corre no passo 3c). No log, as linhas `MODULEBOUNDS`
  comparam o núcleo com a nave inteira.
- **Sem as peças importadas** o jogo continua a funcionar: a nave aparece inteira (`/Game/TestShips/SM_<NAVE>`) e os
  módulos só mudam os stats e as chamas.
- **No código:**
  - `EXMeta.h/.cpp`: o catálogo, as regras, as caixas, a loja, os bots e os prémios;
  - `EXProfile.h/.cpp`: o perfil (versão 2);
  - `EXHangarModel.h/.cpp` e `EXHangarWidget.h/.cpp`: o hangar;
  - `AEXHoverCraft`: os stats, o combustível, o calor, os consumíveis, as peças no casco e a vista em esqueleto;
  - `UEXCraftFx`: os bocais reais e as chamas de cada motor;
  - `AEXRaceDirector`: as perdas, o espólio e os prémios;
  - `AEXHud`: o HUD da corrida.

## 12. Decisões tomadas por omissão (o jogador pode mudar)

- Vidas em vez de casco em percentagem. O casco dos módulos acrescenta vidas.
- Os 6 consumíveis do documento. O escudo do protótipo sai.
- 3 asas por nave, escolhidas entre os 5 tipos do documento, para caberem no estilo de cada nave.
- O ELITE custa 10 000 na demo.

## 13. Estado (2026-10-25)

Feito na nuvem, sem Unreal. A primeira coisa em casa é compilar (`Scripts\casa_tudo.ps1 -SemPista`) e ver se
compila.

**Feito:**
- as peças das 4 naves no Blender: 20 por nave, renders em `modulos.png` e `chamas.png`;
- o catálogo completo do jogo antigo;
- o perfil novo;
- o hangar com os 5 separadores;
- os stats na corrida, o combustível, o calor e os 4 consumíveis;
- as perdas e o espólio com peças reais (os bots levam peças a sério);
- o HUD novo.

**Refeito a pedido do jogador (2026-10-25, tarde):** a blindagem é agora um kit de carroçaria (secção 2) e os
utilitários passaram para dentro do nariz, visíveis só no esqueleto. Imagens em `SourceArt/TestShips/previews/`:
`kit_<nave>.jpg` (a nave sem kit e com os 5) e `utilidade.jpg`.

**A testar no Unreal:**
1. Importar as peças e ver no log as linhas `MODULEBOUNDS`.
2. No hangar, trocar de asa e de blindagem: as peças têm de encaixar na nave sem deslocamento. O kit não pode
   tocar no vidro nem atravessar as asas.
3. Ver o esqueleto e as chamas, que saem dos bocais (se saírem do nariz, o eixo Y dos bocais em `EXHoverCraft.cpp`,
   tabela `ShipNozzles`, está ao contrário). No slot de utilidade, o módulo tem de aparecer no nariz, a brilhar, e
   desaparecer ao sair do esqueleto.
4. Abrir a STANDARD CACHE inicial no COFRE.
5. Correr no Pelotão 15 e ver o espólio no fim.

**Falta:**
- a BASTION nova (asas e peças);
- os slots extra (Aux da NOMAD, Propulsão central da VORTEX, Blindagem 2 da BASTION);
- as passivas das naves;
- o efeito dos sensores;
- som próprio para os consumíveis.
