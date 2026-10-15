# Teste experimental — controlo de voo pelo analógico direito

Esta alteração está numa branch separada e não altera a branch principal `main`.

## Controlos

- **Analógico esquerdo:** direção normal.
- **R2:** acelerar; **L2:** travar.
- **Analógico direito para trás (puxar para baixo):** levantar o nariz e ganhar altitude progressivamente.
- **Analógico direito para a frente (empurrar para cima):** baixar o nariz e descer.
- **Analógico direito na diagonal:** combina atitude de voo com a direção atual; os jatos azul-ciano dos propulsores de manobra dão feedback visual.
- **Analógico direito horizontal:** continua a controlar a órbita horizontal da câmara.
- **R3:** olhar para trás.
- **Teclado no laboratório:** Q/E continuam disponíveis para inclinar no modo de teste; A/D ou setas dirigem e W acelera.

## Como testar

1. Abre o projeto `ExtractStardustRDD` no Unity **6000.3.26f1**.
2. Usa a pista de laboratório/sandbox antes de experimentar a expedição completa.
3. Liga um DualShock 4 ou DualSense e inicia a corrida.
4. Em reta, puxa gradualmente o analógico direito para trás e observa a inclinação e a subida.
5. Empurra-o para a frente e confirma que a nave baixa o nariz.
6. Experimenta diagonais e confirma se os jatos acompanham a manobra.
7. Larga o analógico e confirma que a inclinação regressa suavemente ao neutro.
8. Compara a estabilidade nas curvas, em half-pipes e junto a obstáculos; testa também nitro, derrapagem, colisões e reposicionamento.

## Importante

- É um **protótipo experimental**, não uma build compilada.
- A sustentação adicional depende da velocidade e da inclinação; não garante que a nave consiga subir verticalmente nem passar por cima de qualquer obstáculo.
- A física de hover, aderência e colisões foi preservada, mas precisa de ser validada em execução real.
- Se o controlo parecer demasiado forte/fraco, ajustar os campos `flightPitchGroundMax`, `flightPitchAirMax`, `flightPitchResponse` e `flightLiftExtra` em `CraftTuning.cs`.
- Para reverter o teste, volta à branch `main`; não é necessário alterar os controlos da versão principal.
