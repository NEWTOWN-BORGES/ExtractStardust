// EXTRACT: STARDUST — RED DUST DIVIDE · variação MACRO da cor da geologia.
//
// Porque existe este ficheiro
// ---------------------------
// O RDGeology.shader já faz muita variação de cor, mas toda em escala de 10-40 m (pocket,
// crust, sandCover, gravel, crevice, verniz). Numa parede de 105 km isso lê-se como cor
// uniforme: é textura de perto vista de longe. O resultado era "um corredor castanho com
// faixas da mesma cor ao longo de quilómetros".
//
// Este include acrescenta a variação que faltava, em escalas de 100 m a 4 km:
//   - manchas de cascalho (rocha desfeita, tom mais frio)
//   - veios de areia varrida pelo vento (riscas sub-horizontais claras)
//   - faces lavadas cobertas de verniz (bandas verticais largas e escuras)
//   - arenito fresco exposto (zonas mais claras e quentes)
//   - variação de contexto a ~4 km (nenhuma parede tem a mesma cor do início ao fim)
//   - tufos de vegetação nos patamares e junto ao pé
//
// CUSTO — LER ANTES DE MEXER
// --------------------------
// É ruído 3D por pixel. As rotinas abaixo estão separadas para se poder baixar a qualidade
// medindo, sem tocar na lógica:
//
//   RD_MACRO      1 = liga tudo (0 = desliga e fica como estava)
//   RD_MACRO_FBM3 número de octaves (3 dá ~24 avaliações de ruído; 2 dá ~16; 1 dá ~8)
//   RD_MACRO_FBM2 octaves das manchas mais baratas (2 ou 1)
//
// Cada octave custa 8 avaliações de rd_hash. Referência de ordem de grandeza: 4 camadas a 2
// octaves ≈ 4 × 16 = 64 chamadas a rd_hash por pixel. Isso é mais do que o shader fazia, mas
// continua dentro do normal para um shader de terreno. É para MEDIR, não para assumir.

#ifndef RD_COLOUR_INCLUDED
#define RD_COLOUR_INCLUDED

#include "RDGeology.hlsl"

#ifndef RD_MACRO
#define RD_MACRO 1
#endif
#ifndef RD_MACRO_FBM3
#define RD_MACRO_FBM3 2
#endif
#ifndef RD_MACRO_FBM2
#define RD_MACRO_FBM2 1
#endif

// fbm 3D com octaves em compile-time (rd_noise e rd_fbm vêm de RDGeology.hlsl)
float rd_macro_fbm3(float3 p)
{
    float s = 0.0, a = 0.5, n = 0.0;
    [unroll(RD_MACRO_FBM3)] for (int o = 0; o < RD_MACRO_FBM3; o++)
    {
        s += a * rd_noise(p);
        n += a;
        p = p * 2.03 + float3(5.2, 1.3, 7.7);
        a *= 0.5;
    }
    return s / max(n, 1e-4);
}

float rd_macro_fbm2(float3 p)
{
    float s = 0.0, a = 0.5, n = 0.0;
    [unroll(RD_MACRO_FBM2)] for (int o = 0; o < RD_MACRO_FBM2; o++)
    {
        s += a * rd_noise(p);
        n += a;
        p = p * 2.07 + float3(9.1, 3.3, 6.1);
        a *= 0.5;
    }
    return s / max(n, 1e-4);
}

/// <summary>
/// Aplica a variação macro a uma cor de camada já calculada pelo shader.
/// </summary>
/// <param name="albedo">cor atual (camada + detalhe fino)</param>
/// <param name="pw">posição no mundo</param>
/// <param name="wallU">0 = pé da parede, 1 = topo (use saturate(normal.y) ou a altura normalizada)</param>
/// <param name="seed">0..1, para diferentes paredes não saírem iguais</param>
float3 rd_macro_colour(float3 albedo, float3 pw, float wallU, float seed)
{
#if RD_MACRO
    // eixos do ruído: X ao longo da parede, Y em altura, Z pela face.
    // As escalas estão em metros, divididas diretamente — é isso que dá a escala correta.
    float3 q = float3(pw.x + seed * 731.0, pw.y + seed * 311.0, pw.z + seed * 149.0 + wallU * 60.0);

    // 1. manchas de cascalho: rocha desfeita, tom mais frio (Moss Back / cinza)
    float grav = rd_macro_fbm3(q * (1.0 / 1000.0));
    float mGrav = saturate((grav - 0.45) * 3.33);
    albedo = lerp(albedo, RD_PAL[4] * 0.85, mGrav * 0.45);

    // 2. veios de areia varrida pelo vento: riscas sub-horizontais claras
    float streak = rd_macro_fbm3(float3(q.x, q.y * 0.061, q.z) * (1.0 / 420.0));
    float mStreak = pow(saturate((streak - 0.50) * 3.57), 1.4);
    albedo = lerp(albedo, RD_PAL[12], mStreak * 0.32);

    // 3. faces lavadas: o verniz do deserto cobre mais, bandas verticais largas e escuras
    float wash = rd_macro_fbm3(float3(q.x * 0.26, q.y * 0.04, q.z * 0.26) * (1.0 / 68.0));
    float mWash = saturate((wash - 0.54) * 4.0);
    albedo = lerp(albedo, RD_PAL[13], mWash * 0.38);

    // 4. arenito fresco exposto: zonas mais claras e quentes (Entrada / Navajo rosado)
    float fresh = rd_macro_fbm2(float3(q.x * 0.33, q.y * 0.10, q.z * 0.33) * (1.0 / 600.0));
    float mFresh = saturate((fresh - 0.50) * 3.33);
    albedo = lerp(albedo, RD_PAL[11], mFresh * 0.30);

    // 5. variação de contexto a ~4 km: mata as "faixas iguais durante quilómetros"
    float big = rd_macro_fbm2(float3(q.x * (1.0 / 4000.0), seed * 0.07, q.z * (1.0 / 4000.0)));
    albedo *= (0.82 + 0.36 * big);

    // 6. tufos de vegetação: manchas pequenas e escuras nos patamares e junto ao pé
    float veg = rd_macro_fbm3(q * (1.0 / 55.0));
    float band = saturate((wallU - 0.15) * 3.0) * saturate((0.75 - wallU) * 4.0);
    float mVeg = saturate((veg - 0.62) * 5.0) * band;
    albedo = lerp(albedo, RD_PAL[7], mVeg * 0.45);

    return albedo;
#else
    return albedo;
#endif
}

#endif
