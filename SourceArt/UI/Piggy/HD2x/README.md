# Porquinho mealheiro: versão HD 2×

As mesmas folhas por animação da pasta de cima, ao dobro do tamanho: o porquinho tem ~700 px. Os cortes, as células e
os pivots são os mesmos, multiplicados por 2. Os tamanhos e os retângulos estão em `Piggy_Spritesheet_HD2x.json`.

- **Como:** ampliação por IA com o modelo anime do Real-ESRGAN (`realesr-animevideov3`, licença BSD-3-Clause). O
  modelo amplia 4× e o resultado é reduzido para 2× com filtro de área, para as linhas ficarem limpas. A cor e a
  transparência são ampliadas em separado. O porquinho não é redesenhado, mas o detalhe fino acrescentado é estimado
  pelo modelo e não vem do original.
- **Para quê:** promoção, cartazes e trailers. No jogo usar as folhas da pasta de cima, que já chegam para o HUD.
- **Atenção:** a `Reaction.png` tem 12 174 px de largura. É mais do que o limite de 8192 px de algumas plataformas no
  Unreal (o máximo geral é 16 384). Para a usar como textura, cortá-la em duas linhas.
- **Refazer:** `python3 Scripts/piggy_sprites/upscale_hd.py` (precisa de onnx e onnxruntime; não usa PyTorch). Descarrega
  o modelo (2,5 MB) da primeira vez.
