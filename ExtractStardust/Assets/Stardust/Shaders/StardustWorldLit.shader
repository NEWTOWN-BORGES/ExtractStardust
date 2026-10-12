// Island models (rocks, trees, ruins, colossi, tunnels, vehicles). Albedo = Blender palette colour (vertex colour)
// with PBR detail from a texture array layer (triplanar, world or object space), per-vertex roughness/emission
// (uv2: x roughness, y emission strength), wind sway, leaf translucency and ground occlusion.
// Supports GPU instancing (Graphics.RenderMeshInstanced).
Shader "Stardust/WorldLit"
{
    Properties
    {
        _Albedo ("Albedo + height (array)", 2DArray) = "" {}
        _Normal ("Normal + roughness (array)", 2DArray) = "" {}
        _Layer ("Texture layer (-1 none)", Float) = 0
        _Tiling ("Tiling (m)", Float) = 6
        _Detail ("Texture detail on albedo", Range(0, 1)) = 0.6
        _NormalStrength ("Normal strength", Range(0, 2)) = 1
        _TexRough ("Texture roughness weight", Range(0, 1)) = 0.5
        _Metallic ("Metallic", Range(0, 1)) = 0
        _Emission ("Emission multiplier", Float) = 1
        _Wind ("Wind sway (m)", Float) = 0
        _WindHeight ("Wind full height (m)", Float) = 8
        _Translucency ("Leaf translucency", Range(0, 1)) = 0
        _GroundAO ("Ground occlusion", Range(0, 1)) = 0.35
        _AOHeight ("Ground occlusion height (m)", Float) = 3
        _ObjectSpace ("Object space projection", Float) = 0
        _Tint ("Tint", Color) = (1, 1, 1, 1)
        _Variation ("Per-instance colour variation", Range(0, 0.4)) = 0
        [Enum(UnityEngine.Rendering.CullMode)] _Cull ("Cull", Float) = 2
    }

    HLSLINCLUDE
    #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
    #include "StardustCommon.hlsl"

    CBUFFER_START(UnityPerMaterial)
        float _Layer;
        float _Tiling;
        half _Detail;
        half _NormalStrength;
        half _TexRough;
        half _Metallic;
        half _Emission;
        float _Wind;
        float _WindHeight;
        half _Translucency;
        half _GroundAO;
        float _AOHeight;
        float _ObjectSpace;
        half4 _Tint;
        float _Cull;
        half _Variation;
    CBUFFER_END

    #define SD_VERTEX_OFFSET 1
    float3 SD_VertexOffset(float3 positionWS, float3 positionOS)
    {
        float h = saturate(positionOS.y / _WindHeight);
        float t = _Time.y;
        float s = sin(t * 1.6 + positionWS.x * 0.045 + positionWS.z * 0.037) + 0.35 * sin(t * 3.7 + positionWS.z * 0.11 + positionWS.x * 0.07);
        float f = 0.25 * sin(t * 7.3 + positionWS.x * 0.9 + positionWS.y * 1.3);   // leaf flutter
        return positionWS + float3(s + f, f * 0.4, s * 0.6 - f) * (_Wind * h * h);
    }
    ENDHLSL

    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }

        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            Cull [_Cull]
            ZWrite On

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fragment _ _SCREEN_SPACE_OCCLUSION
            #pragma multi_compile_fog

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "StardustLighting.hlsl"

            TEXTURE2D_ARRAY(_Albedo); SAMPLER(sampler_Albedo);
            TEXTURE2D_ARRAY(_Normal); SAMPLER(sampler_Normal);

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                half4 color : COLOR;
                float2 surf : TEXCOORD1;
                UNITY_VERTEX_INPUT_INSTANCE_ID
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float3 normalWS : TEXCOORD1;
                half4 color : COLOR;
                float3 projPos : TEXCOORD2;
                float3 projNrm : TEXCOORD3;
                half fogFactor : TEXCOORD4;
                half3 surf : TEXCOORD5;   // roughness, emission, height above the model base
                half2 vary : TEXCOORD6;   // per-instance random (colour variation)
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                UNITY_SETUP_INSTANCE_ID(v);
                float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
                positionWS = SD_VertexOffset(positionWS, v.positionOS.xyz);
                o.positionWS = positionWS;
                o.positionCS = TransformWorldToHClip(positionWS);
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.color = v.color;
                o.projPos = _ObjectSpace > 0.5 ? v.positionOS.xyz : positionWS;
                o.projNrm = _ObjectSpace > 0.5 ? v.normalOS : o.normalWS;
                o.fogFactor = ComputeFogFactor(o.positionCS.z);
                o.surf = half3(v.surf.x, v.surf.y, v.positionOS.y);
                float3 org = float3(UNITY_MATRIX_M._m03, UNITY_MATRIX_M._m13, UNITY_MATRIX_M._m23);
                o.vary = half2(SD_Hash(org.xz * 0.013), SD_Hash(org.zx * 0.021 + 7.3));
                return o;
            }

            half4 frag(Varyings i, FRONT_FACE_TYPE face : FRONT_FACE_SEMANTIC) : SV_Target
            {
                half3 n = SD_SafeNormalize(i.normalWS);
                n = IS_FRONT_VFACE(face, n, -n);
                half3 base = SD_SrgbToLinear(i.color.rgb) * _Tint.rgb;
                // every instance a little different (brightness and a warm/cool shift)
                base *= lerp(1.0 - _Variation, 1.0 + _Variation, i.vary.x) * lerp(half3(1.06, 1.0, 0.82), half3(0.92, 1.0, 1.06), lerp(0.5, i.vary.y, saturate(_Variation * 4.0)));
                half3 albedo = base;
                half rough = i.surf.x;
                half3 nrm = n;

                [branch] if (_Layer >= 0)
                {
                    float3 p = i.projPos / _Tiling;
                    half3 pn = SD_SafeNormalize(i.projNrm);
                    float3 bw = pow(abs(pn), 4.0);
                    bw /= max(bw.x + bw.y + bw.z, 1e-5);
                    int layer = (int)_Layer;
                    half4 ax = SAMPLE_TEXTURE2D_ARRAY(_Albedo, sampler_Albedo, p.zy, layer);
                    half4 ay = SAMPLE_TEXTURE2D_ARRAY(_Albedo, sampler_Albedo, p.xz, layer);
                    half4 az = SAMPLE_TEXTURE2D_ARRAY(_Albedo, sampler_Albedo, p.xy, layer);
                    half4 nx = SAMPLE_TEXTURE2D_ARRAY(_Normal, sampler_Normal, p.zy, layer);
                    half4 ny = SAMPLE_TEXTURE2D_ARRAY(_Normal, sampler_Normal, p.xz, layer);
                    half4 nz = SAMPLE_TEXTURE2D_ARRAY(_Normal, sampler_Normal, p.xy, layer);
                    half3 tex = ax.rgb * bw.x + ay.rgb * bw.y + az.rgb * bw.z;
                    // keep the palette colour, take the texture's light/dark structure
                    half lum = dot(tex, half3(0.3, 0.55, 0.15));
                    albedo = base * lerp(1.0, lum * 2.4, _Detail);
                    half3 dn = n * 0.001;
                    if (bw.x > 0.01) dn += SD_ProjectNormal(SD_DecodeNormal(nx, _NormalStrength), n, half3(0, 0, 1), half3(0, 1, 0)) * bw.x;
                    if (bw.y > 0.01) dn += SD_ProjectNormal(SD_DecodeNormal(ny, _NormalStrength), n, half3(1, 0, 0), half3(0, 0, 1)) * bw.y;
                    if (bw.z > 0.01) dn += SD_ProjectNormal(SD_DecodeNormal(nz, _NormalStrength), n, half3(1, 0, 0), half3(0, 1, 0)) * bw.z;
                    nrm = SD_SafeNormalize(dn);
                    rough = lerp(rough, nx.a * bw.x + ny.a * bw.y + nz.a * bw.z, _TexRough);
                }

                half ao = lerp(1.0 - _GroundAO, 1.0, saturate(i.surf.z / _AOHeight));

                InputData inputData = (InputData)0;
                inputData.positionWS = i.positionWS;
                inputData.normalWS = nrm;
                inputData.viewDirectionWS = GetWorldSpaceNormalizeViewDir(i.positionWS);
                inputData.shadowCoord = TransformWorldToShadowCoord(i.positionWS);
                inputData.fogCoord = i.fogFactor;
                inputData.bakedGI = SampleSH(nrm);
                inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(i.positionCS);
                inputData.shadowMask = half4(1, 1, 1, 1);

                SDSurface s;
                s.albedo = albedo;
                s.metallic = _Metallic;
                s.smoothness = saturate(1.0 - rough);
                s.occlusion = ao;
                s.emission = base * i.surf.y * _Emission;
                Light sun;
                half4 color = half4(SD_ShadePBR(inputData, s, sun), 1);
                [branch] if (_Translucency > 0)
                {
                    half back = pow(saturate(dot(inputData.viewDirectionWS, -sun.direction)), 4.0);
                    half wrap = saturate(dot(-n, sun.direction)) * 0.35;
                    color.rgb += albedo * sun.color * (back + wrap) * _Translucency * lerp(0.25, 1.0, sun.shadowAttenuation) * 1.6;
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
            Cull [_Cull]

            HLSLPROGRAM
            #pragma vertex ShadowVert
            #pragma fragment ShadowFrag
            #pragma multi_compile_instancing
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
            Cull [_Cull]

            HLSLPROGRAM
            #pragma vertex DepthVert
            #pragma fragment DepthFrag
            #pragma multi_compile_instancing
            #include "StardustDepth.hlsl"
            ENDHLSL
        }

        Pass
        {
            Name "DepthNormals"
            Tags { "LightMode"="DepthNormals" }
            ZWrite On
            Cull [_Cull]

            HLSLPROGRAM
            #pragma vertex DepthNormalsVert
            #pragma fragment DepthNormalsFrag
            #pragma multi_compile_instancing
            #include "StardustDepth.hlsl"
            ENDHLSL
        }
    }
    Fallback Off
}
