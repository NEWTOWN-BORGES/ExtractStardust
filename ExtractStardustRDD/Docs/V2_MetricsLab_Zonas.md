# Metrics Lab — zonas geradas

Gerado por `RedDust.EditorTools.MetricsLabBuilder`. Não editar à mão.

Cada zona é independente e tem um piso de referência **Slickrock**
(grip 1,08 · topSpeed 1,03 · drag 0), para que as medições dependam da nave
e não do chão. Ver `LabGeometry` para a razão de isto ser obrigatório.

Cena: `Assets/RedDust/Scenes/RDD_MetricsLab.unity`

| Zona | Tipo | Centro (x, y, z) | Raio | Largura | Comprimento | Bank | Parede | Ângulo | Notas |
|---|---|---|---|---|---|---|---|---|---|
| A01_Arranque_Aceleracao | Flat | -400, 0, 2100 | — | 60 | 4000 | — | — | — | Reta plana de 4 km: 0→300 km/h, velocidade máxima com e sem boost, velocidade média. |
| A02_Corredor_Travagem | Flat | -250, 0, 600 | — | 40 | 1200 | — | — | — | Travagem 400→250 km/h e distância de paragem. |
| B01_Raio060_Bank25 | Circle | 1200, 0, 1400 | 60 | 30 | — | 25 | — | — | Velocidade máxima estável com aderência e com derrapagem. |
| B02_Raio120_Bank35 | Circle | 1600, 0, 1800 | 120 | 34 | — | 35 | — | — | Aceleração lateral máxima (g) e raio mínimo por velocidade. |
| B03_Raio250_Bank45 | Circle | 2100, 0, 2400 | 250 | 40 | — | 45 | — | — | Banking sustentável e ângulo máximo antes de perder contacto. |
| B04_Raio500_Bank55 | Circle | 3100, 0, 1500 | 500 | 44 | — | 55 | — | — | Velocidade máxima estável com bank alto. |
| B05_Raio060_Plano | Circle | 900, 0, 2400 | 60 | 30 | — | — | — | — | Referência PLANa no mesmo raio: mede exatamente o ganho que o bank dá. |
| C01_HalfPipe_Largo | HalfPipe | -1200, 0, 1000 | 180 | 40 | — | — | 45 | — | Half-pipe largo a 45°: percurso a 3 alturas, contacto e erro de linha. |
| C02_HalfPipe_Apertado | HalfPipe | -1200, 0, 2400 | 90 | 24 | — | — | 60 | — | Half-pipe apertado a 60°: velocidade mínima para aguentar a parede. |
| D01_Wall45 | Wall | -2000, 0, 700 | — | 40 | 220 | — | 45 | 45 | Wall ride a 45°: segundos em contacto acima da velocidade mínima, e queda previsível abaixo dela. |
| D02_Wall55 | Wall | -2000, 0, 1100 | — | 40 | 220 | — | 55 | 55 | Wall ride a 55°: segundos em contacto acima da velocidade mínima, e queda previsível abaixo dela. |
| D03_Wall65 | Wall | -2000, 0, 1500 | — | 40 | 220 | — | 65 | 65 | Wall ride a 65°: segundos em contacto acima da velocidade mínima, e queda previsível abaixo dela. |
| E01_Transicao_0a30 | BankTransition | -600, 0, -600 | — | 34 | 400 | — | — | — | Taxa de transição (°/m): 30° em 400 m. |
| E02_Transicao_0a50 | BankTransition | -600, 0, -1100 | — | 34 | 400 | — | — | — | Taxa de transição (°/m): 50° em 400 m (mais agressiva). |
| F01_Salto_7deg | Lip | 500, 0, -500 | — | 30 | 40 | — | — | 7 | Flow jump: lábio natural de 7°, mede altura e tempo no ar. |
| F02_Salto_15deg | Lip | 500, 0, -1100 | — | 30 | 46 | — | — | 15 | Salto médio: distância e velocidade de aterragem. |
| F03_Salto_25deg | Lip | 500, 0, -1700 | — | 30 | 52 | — | — | 25 | Salto máximo: velocidade de aterragem que provoca dano (landingHard = 17 m/s). |
| G01_Queda_5m | Drop | 1900, 5, -400 | — | 40 | 60 | — | — | — | Plataforma a 5 m acima de uma zona de aterragem plana: altura máxima sem dano. |
| G02_Queda_15m | Drop | 1900, 15, -800 | — | 40 | 60 | — | — | — | Plataforma a 15 m acima de uma zona de aterragem plana: altura máxima sem dano. |
| G03_Queda_25m | Drop | 1900, 25, -1200 | — | 40 | 60 | — | — | — | Plataforma a 25 m acima de uma zona de aterragem plana: altura máxima sem dano. |
| G04_Queda_35m | Drop | 1900, 35, -1600 | — | 40 | 60 | — | — | — | Plataforma a 35 m acima de uma zona de aterragem plana: altura máxima sem dano. |

## O que falta medir nesta cena

As 8 famílias de métricas da secção C do plano são recolhidas pelo executor:

```
Unity -batchmode -projectPath . -executeMethod RedDust.EditorTools.MetricsLabRunner.Run -metricsDir Temp/Metrics
```

Escreve um CSV por chassis em `Temp/Metrics/`.
