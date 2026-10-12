// EXTRACT: STARDUST — RED DUST DIVIDE · funções partilhadas: ruído, paleta das camadas, perspetiva aérea.
#ifndef RD_GEOLOGY_INCLUDED
#define RD_GEOLOGY_INCLUDED

float rd_hash(float3 p)
{
    p = frac(p * 0.3183099 + float3(0.71, 0.113, 0.419));
    p *= 17.0;
    return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float rd_noise(float3 x)
{
    float3 i = floor(x);
    float3 f = frac(x);
    f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(lerp(rd_hash(i + float3(0, 0, 0)), rd_hash(i + float3(1, 0, 0)), f.x),
                     lerp(rd_hash(i + float3(0, 1, 0)), rd_hash(i + float3(1, 1, 0)), f.x), f.y),
                lerp(lerp(rd_hash(i + float3(0, 0, 1)), rd_hash(i + float3(1, 0, 1)), f.x),
                     lerp(rd_hash(i + float3(0, 1, 1)), rd_hash(i + float3(1, 1, 1)), f.x), f.y), f.z);
}

float rd_fbm(float3 p, int octaves)
{
    float a = 0.5, s = 0.0, n = 0.0;
    [unroll(4)] for (int o = 0; o < octaves; o++)
    {
        s += a * rd_noise(p);
        n += a;
        p = p * 2.03 + float3(17.1, 3.7, 9.2);
        a *= 0.5;
    }
    return s / n;
}

// Paleta das camadas (linear) — mesma ordem que rdd_geology.PALETTE (Blender)
static const float3 RD_PAL[14] =
{
    float3(0.3050, 0.0482, 0.0212),   // 0  Organ Rock
    float3(0.7605, 0.6724, 0.5149),   // 1  White Rim
    float3(0.2623, 0.0648, 0.0319),   // 2  Moenkopi
    float3(0.3916, 0.1221, 0.0612),   // 3  Moenkopi claro
    float3(0.4851, 0.4020, 0.2831),   // 4  Moss Back
    float3(0.4125, 0.0931, 0.0513),   // 5  Chinle vermelho
    float3(0.2159, 0.1070, 0.1384),   // 6  Chinle púrpura
    float3(0.3050, 0.3050, 0.2232),   // 7  Chinle cinza-esverdeado
    float3(0.5520, 0.1221, 0.0343),   // 8  Wingate
    float3(0.3050, 0.0887, 0.0545),   // 9  Kayenta
    float3(0.7305, 0.5149, 0.3050),   // 10 Navajo
    float3(0.6724, 0.3515, 0.2159),   // 11 Navajo/Entrada rosado
    float3(0.6172, 0.3050, 0.1274),   // 12 areia
    float3(0.0212, 0.0116, 0.0091),   // 13 verniz do deserto
};

float3 rd_pal(float v) { return RD_PAL[clamp((int)round(v * 15.0), 0, 13)]; }

// "Verniz do deserto": escorrências escuras verticais a partir das saliências, em faces íngremes.
float rd_varnish(float3 pw, float steep)
{
    float streak = rd_noise(float3(pw.x * 0.45, pw.y * 0.035, pw.z * 0.45));
    float body = rd_noise(pw * float3(0.08, 0.02, 0.08));
    float v = saturate((streak * 0.7 + body * 0.5 - 0.6) * 3.0);
    return v * saturate((steep - 0.5) * 2.5);
}

// Perspetiva aérea: névoa com queda em altura; quente em direção ao sol, azul-violeta nas distâncias à sombra.
float4 _RD_FogColor;      // rgb: cor do horizonte · a: densidade (1/m)
float4 _RD_FogSun;        // rgb: cor de dispersão para o sol · a: potência do lóbulo
float4 _RD_FogShadow;     // rgb: cor das distâncias contra o sol (azul-violeta) · a: altura de referência
float4 _RD_FogParams;     // x: queda em altura (1/m), y: opacidade máxima

float3 rd_aerial(float3 color, float3 pw, float3 camPos, float3 sunDir)
{
    float3 v = pw - camPos;
    float dist = length(v);
    float3 vd = v / max(dist, 1e-3);
    float dens = _RD_FogColor.a;
    // integral da densidade com queda exponencial em altura entre a câmera e o ponto
    float h0 = camPos.y - _RD_FogShadow.a;
    float fall = _RD_FogParams.x;
    float dy = vd.y * dist * fall;
    float heightTerm = exp(-max(h0, -200.0) * fall) * ((abs(dy) > 1e-4) ? (1.0 - exp(-dy)) / dy : 1.0);
    float od = dens * dist * heightTerm;
    float fog = saturate(1.0 - exp(-od)) * _RD_FogParams.y;
    float sunAmt = pow(saturate(dot(vd, sunDir)), _RD_FogSun.a);
    float3 fogCol = lerp(_RD_FogShadow.rgb, _RD_FogColor.rgb, saturate(0.55 + 0.45 * vd.y + 0.3 * sunAmt));
    fogCol = lerp(fogCol, _RD_FogSun.rgb, sunAmt);
    return lerp(color, fogCol, fog);
}

#endif
