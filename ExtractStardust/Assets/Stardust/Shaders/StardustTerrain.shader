// Island terrain: 8 PBR layers (Texture2DArray) blended by the biome map, slope (triplanar rock),
// road mask and shoreline, with height-aware blending, macro variation, URP lighting, shadows and fog.
Shader "Stardust/Terrain"
{
    Properties
    {
        _Albedo ("Albedo + height (array)", 2DArray) = "" {}
        _Normal ("Normal + roughness (array)", 2DArray) = "" {}
        _Biome ("Biome map (R grass, G moss, B red, A white)", 2D) = "black" {}
        _Roads ("Road mask", 2D) = "black" {}
        _WorldSize ("World size (m)", Float) = 24576
        _Tiling ("Ground tiling (m)", Float) = 7
        _RockTiling ("Rock tiling (m)", Float) = 16
        _NormalStrength ("Normal strength", Range(0, 2)) = 1
        _Quality ("Quality (0 low, 1 high)", Float) = 1
    }

    HLSLINCLUDE
    #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
    ENDHLSL

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry-100" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            Cull Back
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "StardustCommon.hlsl"
            #include "StardustLighting.hlsl"

            TEXTURE2D_ARRAY(_Albedo); SAMPLER(sampler_Albedo);
            TEXTURE2D_ARRAY(_Normal); SAMPLER(sampler_Normal);
            TEXTURE2D(_Biome); SAMPLER(sampler_Biome);
            TEXTURE2D(_Roads); SAMPLER(sampler_Roads);
            float _SD_Debug;

            CBUFFER_START(UnityPerMaterial)
                float _WorldSize;
                float _Tiling;
                float _RockTiling;
                half _NormalStrength;
                half _Quality;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                half fogFactor : TEXCOORD2;
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                VertexPositionInputs p = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.positionWS = p.positionWS;
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.fogFactor = ComputeFogFactor(p.positionCS.z);
                return o;
            }

            void Layer(int i, float w, float2 uv, half3 n, inout half3 accA, inout half3 accN, inout half accR, inout float wsum)
            {
                [branch] if (w > 0.012)
                {
                    half4 a = SAMPLE_TEXTURE2D_ARRAY(_Albedo, sampler_Albedo, uv, i);
                    half4 t = SAMPLE_TEXTURE2D_ARRAY(_Normal, sampler_Normal, uv, i);
                    float wi = w * (0.35 + a.a);
                    accA += a.rgb * wi;
                    accN += SD_ProjectNormal(SD_DecodeNormal(t, _NormalStrength), n, half3(1, 0, 0), half3(0, 0, 1)) * wi;
                    accR += t.a * wi;
                    wsum += wi;
                }
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 pos = i.positionWS;
                half3 n = SD_SafeNormalize(i.normalWS);
                float2 mapUV = pos.xz / _WorldSize + 0.5;
                half4 bio = SAMPLE_TEXTURE2D(_Biome, sampler_Biome, mapUV);
                half road = SAMPLE_TEXTURE2D(_Roads, sampler_Roads, mapUV).r;
                float slope = 1.0 - n.y;
                float patch = SD_Fbm(pos.xz / 140.0);

                // sequential blend, the same order as the minimap: sand -> white -> red -> grass -> moss
                float w0 = 1, w1 = 0, w2 = 0, w3 = 0, w4 = 0, w5 = 0, w6 = 0, w7 = 0;
                float a = saturate(bio.a * (1 - bio.r) * 0.85);
                w0 *= 1 - a; w4 = a;
                a = saturate(bio.b * 0.85);
                w0 *= 1 - a; w4 *= 1 - a; w3 = a;
                a = saturate(bio.r * (0.75 + 0.45 * patch));
                w0 *= 1 - a; w4 *= 1 - a; w3 *= 1 - a; w1 = a;
                a = saturate(bio.g * (0.7 + 0.5 * patch));
                w0 *= 1 - a; w4 *= 1 - a; w3 *= 1 - a; w1 *= 1 - a; w2 = a;
                // wet sand along the shore
                a = (1 - smoothstep(0.8, 3.2, pos.y)) * 0.9 * (1 - smoothstep(0.25, 0.5, slope));
                w0 *= 1 - a; w1 *= 1 - a; w2 *= 1 - a; w3 *= 1 - a; w4 *= 1 - a; w7 = a;
                // rock on steep ground
                a = smoothstep(0.28, 0.5, slope + (patch - 0.5) * 0.12);
                w0 *= 1 - a; w1 *= 1 - a; w2 *= 1 - a; w3 *= 1 - a; w4 *= 1 - a; w7 *= 1 - a; w5 = a;
                // the race roads
                a = saturate(road * 1.05) * (1 - smoothstep(0.45, 0.7, slope));
                w0 *= 1 - a; w1 *= 1 - a; w2 *= 1 - a; w3 *= 1 - a; w4 *= 1 - a; w5 *= 1 - a; w7 *= 1 - a; w6 = a;

                float2 uv = pos.xz / _Tiling;
                half3 accA = 0, accN = 0; half accR = 0; float wsum = 0;
                Layer(0, w0, uv, n, accA, accN, accR, wsum);
                Layer(1, w1, uv, n, accA, accN, accR, wsum);
                Layer(2, w2, uv * 0.8, n, accA, accN, accR, wsum);
                Layer(3, w3, uv * 0.7, n, accA, accN, accR, wsum);
                Layer(4, w4, uv, n, accA, accN, accR, wsum);
                Layer(6, w6, uv * 1.4, n, accA, accN, accR, wsum);
                Layer(7, w7, uv, n, accA, accN, accR, wsum);

                // rock: triplanar on PC, dominant-axis projection on low quality
                [branch] if (w5 > 0.012)
                {
                    float3 bw = pow(abs(n), 4.0);
                    bw /= max(bw.x + bw.y + bw.z, 1e-5);
                    float s = 1.0 / _RockTiling;
                    half4 ax = 0, ay = 0, az = 0, nx = 0, ny = 0, nz = 0;
                    if (_Quality < 0.5)
                    {
                        float m = max(bw.x, max(bw.y, bw.z));
                        bw = float3(bw.x >= m, bw.y >= m && bw.x < m, bw.z >= m && bw.x < m && bw.y < m);
                    }
                    [branch] if (bw.x > 0.01) { ax = SAMPLE_TEXTURE2D_ARRAY(_Albedo, sampler_Albedo, pos.zy * s, 5); nx = SAMPLE_TEXTURE2D_ARRAY(_Normal, sampler_Normal, pos.zy * s, 5); }
                    [branch] if (bw.y > 0.01) { ay = SAMPLE_TEXTURE2D_ARRAY(_Albedo, sampler_Albedo, pos.xz * s, 5); ny = SAMPLE_TEXTURE2D_ARRAY(_Normal, sampler_Normal, pos.xz * s, 5); }
                    [branch] if (bw.z > 0.01) { az = SAMPLE_TEXTURE2D_ARRAY(_Albedo, sampler_Albedo, pos.xy * s, 5); nz = SAMPLE_TEXTURE2D_ARRAY(_Normal, sampler_Normal, pos.xy * s, 5); }
                    half4 ra = ax * bw.x + ay * bw.y + az * bw.z;
                    half3 rn = 0;
                    if (bw.x > 0.01) rn += SD_ProjectNormal(SD_DecodeNormal(nx, _NormalStrength), n, half3(0, 0, 1), half3(0, 1, 0)) * bw.x;
                    if (bw.y > 0.01) rn += SD_ProjectNormal(SD_DecodeNormal(ny, _NormalStrength), n, half3(1, 0, 0), half3(0, 0, 1)) * bw.y;
                    if (bw.z > 0.01) rn += SD_ProjectNormal(SD_DecodeNormal(nz, _NormalStrength), n, half3(1, 0, 0), half3(0, 1, 0)) * bw.z;
                    half rr = nx.a * bw.x + ny.a * bw.y + nz.a * bw.z;
                    // warm sandstone tint in the dry biomes, cool grey in the green ones
                    half dry = saturate(1.0 - bio.r - bio.g);
                    half3 tint = lerp(half3(0.95, 0.97, 1.0), half3(1.45, 1.02, 0.74), dry);
                    tint = lerp(tint, half3(1.6, 0.85, 0.62), bio.b);
                    float wi = w5 * (0.35 + ra.a);
                    accA += ra.rgb * tint * wi;
                    accN += rn * wi;
                    accR += rr * wi;
                    wsum += wi;
                }

                wsum = max(wsum, 1e-4);
                half3 albedo = accA / wsum;
                half3 nrm = SD_SafeNormalize(accN / wsum + n * 0.01);
                half rough = accR / wsum;
                // macro variation: large patches of light/dark, so the tiling never shows from the air
                float macro = SD_Fbm(pos.xz / 420.0 + 13.7);
                albedo *= lerp(0.8, 1.14, macro);
                albedo *= lerp(1.0, 0.86, smoothstep(0.55, 0.9, SD_Noise(pos.xz / 55.0)) * (1 - w6));

                InputData inputData = (InputData)0;
                inputData.positionWS = pos;
                inputData.normalWS = nrm;
                inputData.viewDirectionWS = GetWorldSpaceNormalizeViewDir(pos);
                inputData.shadowCoord = TransformWorldToShadowCoord(pos);
                inputData.fogCoord = i.fogFactor;
                inputData.bakedGI = SampleSH(nrm);
                inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS);
                inputData.shadowMask = half4(1, 1, 1, 1);

                SDSurface s;
                s.albedo = albedo;
                s.metallic = 0;
                s.smoothness = saturate((1.0 - rough) * 0.6 + w7 * 0.35);
                s.occlusion = 1;
                s.emission = 0;
                Light sunLight;
                half4 color = half4(SD_ShadePBR(inputData, s, sunLight), 1);
                [branch] if (_SD_Debug > 0.5)
                {
                    Light dl = GetMainLight(inputData.shadowCoord);
                    if (_SD_Debug < 1.5) return half4(dl.shadowAttenuation.xxx, 1);
                    if (_SD_Debug < 2.5) return half4(saturate(dot(nrm, dl.direction)).xxx, 1);
                    if (_SD_Debug < 3.5) return half4(nrm * 0.5 + 0.5, 1);
                    if (_SD_Debug < 4.5) return half4(albedo, 1);
                    if (_SD_Debug < 5.5) return half4(SampleSH(nrm), 1);
                    if (_SD_Debug < 6.5) return half4(dl.color * 0.3, 1);
                    if (_SD_Debug < 7.5) return color;
                    if (_SD_Debug < 8.5) return half4(albedo * (saturate(dot(nrm, dl.direction)) * dl.color * dl.shadowAttenuation + SampleSH(nrm)), 1);
                    if (_SD_Debug < 9.5)
                    {
                    #if defined(_SCREEN_SPACE_OCCLUSION)
                        AmbientOcclusionFactor ao = GetScreenSpaceAmbientOcclusion(inputData.normalizedScreenSpaceUV);
                        return half4(ao.indirectAmbientOcclusion, ao.directAmbientOcclusion, 0, 1);
                    #else
                        return half4(0, 0, 1, 1);
                    #endif
                    }
                    return half4(i.fogFactor.xxx, 1);
                }
                color.rgb = MixFog(color.rgb, inputData.fogCoord);
                color.a = 1;
                return color;
            }
            ENDHLSL
        }

        Pass
        {
            Name "ShadowCaster"
            Tags { "LightMode"="ShadowCaster" }
            ZWrite On
            ZTest LEqual
            ColorMask 0
            Cull Back

            HLSLPROGRAM
            #pragma vertex ShadowVert
            #pragma fragment ShadowFrag
            #pragma multi_compile_vertex _ _CASTING_PUNCTUAL_LIGHT_SHADOW
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"
            #include "StardustShadow.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthOnly"
            Tags { "LightMode"="DepthOnly" }
            ZWrite On
            ColorMask R
            Cull Back

            HLSLPROGRAM
            #pragma vertex DepthVert
            #pragma fragment DepthFrag
            #include "StardustDepth.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            ZWrite On
            Cull Back

            HLSLPROGRAM
            #pragma vertex DepthNormalsVert
            #pragma fragment DepthNormalsFrag
            #include "StardustDepth.hlsl"
            ENDHLSL
        }
    }
    Fallback Off
}
