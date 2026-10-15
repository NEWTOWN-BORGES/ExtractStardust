// EXTRACT: STARDUST — RED DUST DIVIDE · geologia esculpida no Blender.
// Vértice: cor R = classe (0 areia do leito, .25 slickrock, .5 parede de corrida polida, .75 falésia/rocha, 1 planalto/talus)
//          cor G/B = índices de paleta A/B da camada (÷15) · cor A = máscara da zona de corrida
//          UV2 = (dureza da camada, mistura A/B).
Shader "RedDust/Geology"
{
    Properties
    {
        _DetailScale ("Escala do detalhe", Float) = 1
        _BumpStrength ("Relevo de detalhe", Range(0, 2)) = 1
        _Specular ("Especular", Range(0, 1)) = 0.16
        [Tooltip("Variacao de cor em escala grande (100 m a 4 km). 0 desliga e volta ao aspeto anterior.")]
        _MacroAmount ("Variacao macro da cor", Range(0, 1)) = 1
        [Tooltip("Normal map de rocha: fissuras e granulado abaixo do que a geometria resolve.")]
        [Normal] _NormalMap ("Normal map da rocha", 2D) = "bump" {}
        _NormalScale ("Forca do normal map", Range(0, 3)) = 1
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }

        HLSLINCLUDE
        #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
        TEXTURE2D(_NormalMap);
        SAMPLER(sampler_NormalMap);
        CBUFFER_START(UnityPerMaterial)
            float4 _NormalMap_ST;
            float _DetailScale;
            float _BumpStrength;
            float _Specular;
            float _MacroAmount;
            float _NormalScale;
        CBUFFER_END
        ENDHLSL

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile _ RD_LOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "RDGeology.hlsl"
            #include "RDColour.hlsl"

            float _RD_Grid;
            // Limites verticais da geologia: x = cota mínima, y = amplitude (m).
            // Usados para normalizar a altura da parede (pé = 0, topo = 1) na variação macro
            // da cor. Se ninguém os definir, os valores por omissão cobrem uma parede de 300 m.
            float4 _RD_GeoBounds = float4(-200.0, 300.0, 0.0, 0.0);

            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; float4 color : COLOR; float2 uv : TEXCOORD0; float2 uv2 : TEXCOORD1; };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                float4 color : TEXCOORD2;
                float4 uv : TEXCOORD3;
                float2 uvMain : TEXCOORD4;
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionWS = TransformObjectToWorld(v.positionOS.xyz);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.positionCS = TransformWorldToHClip(o.positionWS);
                o.color = v.color;
                o.uv = float4(v.uv, v.uv2);
                o.uvMain = v.uv;
                return o;
            }

            float gridLine(float2 p, float spacing, float width)
            {
                float2 q = p / spacing;
                float2 g = abs(frac(q + 0.5) - 0.5) * spacing;
                float2 fw = max(fwidth(q) * spacing * 1.5, width.xx);
                float2 l = 1.0 - saturate(g / fw);
                return max(l.x, l.y) * saturate(width / max(fw.x, fw.y) * 1.5);
            }

            float2 grid(float3 pw, float3 n)
            {
                float3 w = pow(abs(n), 4.0); w /= max(1e-4, w.x + w.y + w.z);
                float l10 = gridLine(pw.zy, 10.0, 0.14) * w.x + gridLine(pw.xz, 10.0, 0.14) * w.y + gridLine(pw.xy, 10.0, 0.14) * w.z;
                float l2 = gridLine(pw.zy, 2.0, 0.05) * w.x + gridLine(pw.xz, 2.0, 0.05) * w.y + gridLine(pw.xy, 2.0, 0.05) * w.z;
                return float2(l10, l2);
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 pw = i.positionWS;
                float3 n0 = normalize(i.normalWS);
                float3 n = n0;
                float cls = i.color.r, ride = i.color.a;
                float hard = i.uv.z, mixv = i.uv.w;
                float steep = 1.0 - saturate(n0.y);
                float camDist = distance(pw, _WorldSpaceCameraPos);
                float near = saturate(1.0 - camDist / 260.0);

                // classes (passo de 0,125): areia, areia funda, slickrock, cascalho, parede polida, rocha rugosa, falésia, planalto
                float wSand = saturate(1.0 - abs(cls - 0.0) * 8.0);
                float wDeep = saturate(1.0 - abs(cls - 0.125) * 8.0);
                float wSlick = saturate(1.0 - abs(cls - 0.25) * 8.0);
                float wGravel = saturate(1.0 - abs(cls - 0.375) * 8.0);
                float wPolish = saturate(1.0 - abs(cls - 0.5) * 8.0);
                float wRough = saturate(1.0 - abs(cls - 0.625) * 8.0);
                float wTop = saturate((cls - 0.875) * 8.0);
                float wRock = saturate(1.0 - wSand - wDeep - wSlick - wGravel - wPolish - wRough - wTop);
                wSand += wDeep;                           // a areia funda partilha a base da areia

                // cor da camada: duas cores da paleta misturadas por manchas + laminações finas pela altura
                float3 cA = rd_pal(i.color.g), cB = rd_pal(i.color.b);
                float lam = rd_noise(float3(pw.x * 0.04, pw.y * 1.7 + rd_noise(pw * 0.02) * 3.0, pw.z * 0.04));
                float3 rock = lerp(cA, cB, saturate(mixv + (lam - 0.5) * 0.35));
                rock *= lerp(0.88, 1.1, lam);
                rock *= lerp(0.93, 1.05, hard);

            #if !defined(RD_LOW)
                // relevo de detalhe: rocha rugosa perto; areia com ondulação subtil que desvanece com a distância
                float f = 0.55 * _DetailScale;
                float e = 0.35;
                float3 q = pw * f;
                float h0 = rd_fbm(q, 3);
                float3 gr = float3(rd_fbm(q + float3(e, 0, 0), 3), rd_fbm(q + float3(0, e, 0), 3), rd_fbm(q + float3(0, 0, e), 3)) - h0;
                float bump = _BumpStrength * (wRock * 0.85 + wRough * 1.0 + wGravel * 0.7 + wSlick * 0.3 + wPolish * 0.2 + (wSand + wTop) * 0.12) * (0.35 + 0.65 * near);
                float3 g = gr / e * bump * 0.6;
                float rp = dot(pw.xz, float2(0.83, 0.55)) * 5.5 + rd_noise(pw * 0.2) * 7.0;
                g += float3(0.83, 0, 0.55) * cos(rp) * 0.05 * (wSand + wTop) * _BumpStrength * near * saturate(n0.y);
                n = normalize(n - (g - n * dot(g, n)));
            #endif

                // Normal map de rocha: fissuras e granulado finos, que a geometria não resolve
                // (abaixo de ~4 m exigiria ~1 M de triângulos por parede). Só a componente
                // perpendicular à superfície é usada: o bump geométrico acima já deu as
                // tangentes, e inventá-las em UV que podem não existir seria pior.
                float nmFade = saturate(1.0 - camDist / 320.0);
                if (_NormalScale > 0.001 && nmFade > 0.01)
                {
                    float3 nm = UnpackNormalScale(SAMPLE_TEXTURE2D(_NormalMap, sampler_NormalMap,
                                                                    i.uvMain * _NormalMap_ST.xy + _NormalMap_ST.zw),
                                                  _NormalScale);
                    n = normalize(n - n0 * nm.z * 0.6 * nmFade);
                }

                // materiais
                float3 sandCol = lerp(RD_PAL[12] * 0.88, RD_PAL[12] * 1.05, rd_noise(pw * 0.03));
                float3 slick = lerp(rock, RD_PAL[12], 0.25) * lerp(0.93, 1.06, rd_noise(float3(pw.x * 0.04, pw.y * 0.9 + pw.x * 0.2, pw.z * 0.04)));
                float3 polish = lerp(rock, RD_PAL[12], 0.18) * lerp(0.9, 1.04, rd_noise(pw * float3(0.02, 0.4, 0.02)));
                // topo do planalto: arenito com areia nas depressões e crosta biológica escura
                float pocket = smoothstep(0.35, 0.85, rd_noise(pw * float3(0.012, 0, 0.012)) * 0.7 + rd_noise(pw * 0.05) * 0.3) * 0.6;
                float3 top = lerp(rock, sandCol, pocket * saturate(n0.y * 1.4 - 0.4));
                float crust = smoothstep(0.62, 0.8, rd_noise(pw * float3(0.18, 0.0, 0.18))) * saturate(n0.y * 2.0 - 1.2) * (1.0 - ride);
                top = lerp(top, top * 0.6, crust * 0.35);
                // areia funda: mais escura e solta (marcas de vento suaves); cascalho: seixos claros/escuros; rocha rugosa
                float3 deepCol = sandCol * lerp(0.78, 0.9, rd_noise(pw * 0.35));
                float peb = rd_noise(pw * 2.2);
                float3 gravel = lerp(sandCol * 0.75, lerp(RD_PAL[4], rock, 0.5), smoothstep(0.35, 0.75, peb)) * lerp(0.75, 1.1, rd_noise(pw * 5.0));
                float3 rough = rock * lerp(0.7, 0.95, rd_noise(pw * 0.8));
                float3 albedo = lerp(sandCol, deepCol, wDeep / max(wSand, 1e-3)) * wSand + slick * wSlick + gravel * wGravel
                              + polish * wPolish + rough * wRough + top * wTop + rock * wRock;
                // areia acumulada nas saliências planas da rocha
                float sandCover = saturate((n0.y - 0.8) * 6.0) * (wRock + wRough * 0.5) * (0.5 + 0.5 * rd_noise(pw * 0.11));
                albedo = lerp(albedo, sandCol, sandCover);
                // verniz do deserto nas faces íngremes das camadas duras
                albedo = lerp(albedo, RD_PAL[13], rd_varnish(pw, steep) * 0.55 * hard * (wRock + 0.3 * wPolish));

                // grelha de medição (laboratório, tecla G): só na zona de corrida
                float2 gl = grid(pw, n0);
                float gm = _RD_Grid * saturate(ride * 1.5 - 0.3);
                albedo = lerp(albedo, float3(0.85, 0.95, 1.0), gm * (gl.x * 0.55 + gl.y * 0.18));

                // variação MACRO da cor (RDColour.hlsl): 100 m a 4 km.
                // É isto que impede as paredes de serem faixas da mesma cor durante quilómetros.
                // wallU: 0 no pé da parede, 1 no topo, a partir dos limites da geologia.
                float span = max(_RD_GeoBounds.y, 1.0);
                float wallU = saturate((pw.y - _RD_GeoBounds.x) / span);
                float3 macro = rd_macro_colour(albedo, pw, wallU, ride);
                albedo = lerp(albedo, macro, _MacroAmount);

                // iluminação
                Light sun = GetMainLight(TransformWorldToShadowCoord(pw));
                float ndl = saturate(dot(n, sun.direction));
                float3 view = GetWorldSpaceNormalizeViewDir(pw);
                float3 hv = normalize(sun.direction + view);
                float spec = pow(saturate(dot(n, hv)), 28.0) * _Specular * (wSlick + wPolish * 1.2 + 0.2);
                float3 indirect = SampleSH(n);
                float aoD = 1.0, aoI = 1.0;
            #if defined(_SCREEN_SPACE_OCCLUSION)
                AmbientOcclusionFactor ao = GetScreenSpaceAmbientOcclusion(GetNormalizedScreenSpaceUV(i.positionCS));
                aoD = ao.directAmbientOcclusion; aoI = ao.indirectAmbientOcclusion;
            #endif
                float crevice = lerp(1.0, 0.72, saturate(steep * (1.0 - hard)) * wRock);
                float3 color = albedo * (sun.color * (sun.shadowAttenuation * ndl * aoD) + indirect * aoI * crevice)
                             + sun.color * sun.shadowAttenuation * spec * ndl;
                color = rd_aerial(color, pw, _WorldSpaceCameraPos, sun.direction);
                return half4(color, 1);
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ZWrite On ZTest LEqual ColorMask 0
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"
            float3 _LightDirection;
            float3 _LightPosition;
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; };
            Varyings vert(Attributes v)
            {
                Varyings o;
                float3 pw = TransformObjectToWorld(v.positionOS.xyz);
                float3 nw = TransformObjectToWorldNormal(v.normalOS);
            #if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
                float3 ld = normalize(_LightPosition - pw);
            #else
                float3 ld = _LightDirection;
            #endif
                float4 cs = TransformWorldToHClip(ApplyShadowBias(pw, nw, ld));
            #if UNITY_REVERSED_Z
                cs.z = min(cs.z, UNITY_NEAR_CLIP_VALUE);
            #else
                cs.z = max(cs.z, UNITY_NEAR_CLIP_VALUE);
            #endif
                o.positionCS = cs;
                return o;
            }
            half4 frag(Varyings i) : SV_Target { return 0; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ZWrite On ColorMask R
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; };
            Varyings vert(Attributes v) { Varyings o; o.positionCS = TransformObjectToHClip(v.positionOS.xyz); return o; }
            half frag(Varyings i) : SV_Target { return i.positionCS.z; }
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            ZWrite On
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fragment _ _GBUFFER_NORMALS_OCT
            struct Attributes { float4 positionOS : POSITION; float3 normalOS : NORMAL; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 normalWS : TEXCOORD0; };
            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                return o;
            }
            half4 frag(Varyings i) : SV_Target
            {
                float3 n = normalize(i.normalWS);
            #if defined(_GBUFFER_NORMALS_OCT)
                float2 oct = PackNormalOctQuadEncode(n);
                return half4(PackFloat2To888(saturate(oct * 0.5 + 0.5)), 0.0);
            #else
                return half4(n, 0.0);
            #endif
            }
            ENDHLSL
        }
    }
    Fallback Off
}
