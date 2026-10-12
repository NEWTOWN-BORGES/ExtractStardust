// Ocean and lakes: two scrolling normal maps, fresnel sky reflection, sun glint, depth tint near the camera,
// shoreline foam from the scene depth (PC) and the island mask so the sea never shows inside the land.
Shader "Stardust/Water"
{
    Properties
    {
        _WaveNormal ("Wave normal", 2D) = "bump" {}
        _OceanMask ("Ocean mask (world)", 2D) = "white" {}
        _UseMask ("Use ocean mask", Float) = 1
        _WorldSize ("World size (m)", Float) = 24576
        _Deep ("Deep colour", Color) = (0.02, 0.11, 0.16, 1)
        _Shallow ("Shallow colour", Color) = (0.06, 0.36, 0.38, 1)
        _SkyHorizon ("Sky horizon", Color) = (0.62, 0.74, 0.86, 1)
        _SkyZenith ("Sky zenith", Color) = (0.2, 0.42, 0.72, 1)
        _WaveScale ("Wave scale (m)", Float) = 38
        _WaveSpeed ("Wave speed", Float) = 0.6
        _WaveStrength ("Wave strength", Range(0, 2)) = 0.7
        _Foam ("Shore foam", Range(0, 2)) = 1
        _Quality ("Quality (0 low, 1 high)", Float) = 1
    }

    SubShader
    {
        Tags { "RenderType"="Transparent" "RenderPipeline"="UniversalPipeline" "Queue"="Transparent-50" }

        Pass
        {
            Name "Water"
            Tags { "LightMode"="UniversalForward" }
            Cull Back
            ZWrite On
            Blend SrcAlpha OneMinusSrcAlpha

            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fog
            #pragma shader_feature_local _SD_DEPTH_FOAM

            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/DeclareDepthTexture.hlsl"
            #include "StardustCommon.hlsl"

            TEXTURE2D(_WaveNormal); SAMPLER(sampler_WaveNormal);
            TEXTURE2D(_OceanMask); SAMPLER(sampler_OceanMask);

            CBUFFER_START(UnityPerMaterial)
                float _UseMask;
                float _WorldSize;
                half4 _Deep;
                half4 _Shallow;
                half4 _SkyHorizon;
                half4 _SkyZenith;
                float _WaveScale;
                float _WaveSpeed;
                half _WaveStrength;
                half _Foam;
                half _Quality;
            CBUFFER_END

            struct Attributes
            {
                float4 positionOS : POSITION;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                float4 screenPos : TEXCOORD1;
                half fogFactor : TEXCOORD2;
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                VertexPositionInputs p = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = p.positionCS;
                o.positionWS = p.positionWS;
                o.screenPos = ComputeScreenPos(p.positionCS);
                o.fogFactor = ComputeFogFactor(p.positionCS.z);
                return o;
            }

            half3 WaveNormal(float2 uv)
            {
                half3 n = SAMPLE_TEXTURE2D(_WaveNormal, sampler_WaveNormal, uv).rgb * 2.0h - 1.0h;
                return n;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 pos = i.positionWS;
                if (_UseMask > 0.5)
                {
                    half m = SAMPLE_TEXTURE2D(_OceanMask, sampler_OceanMask, pos.xz / _WorldSize + 0.5).r;
                    float inside = all(abs(pos.xz) < _WorldSize * 0.5);
                    clip(lerp(1.0, m - 0.5, inside));
                }

                float3 toCam = _WorldSpaceCameraPos - pos;
                float dist = length(toCam);
                half3 V = toCam / dist;
                float t = _Time.y * _WaveSpeed;
                float2 uv = pos.xz / _WaveScale;
                half3 n1 = WaveNormal(uv + float2(t * 0.05, t * 0.031));
                half3 n2 = WaveNormal(uv * 0.37 + float2(-t * 0.021, t * 0.017));
                half3 n3 = WaveNormal(uv * 2.9 + float2(t * 0.09, -t * 0.07));
                half3 nt = n1 + n2 * 0.8 + n3 * 0.35 * _Quality;
                // waves calm down with distance (less aliasing, the far sea looks like a mirror)
                half strength = _WaveStrength * lerp(1.0, 0.25, saturate(dist / 2500.0));
                half3 N = normalize(half3(nt.x * strength, 1.0, nt.y * strength));

                Light sun = GetMainLight(TransformWorldToShadowCoord(pos));
                half NdotV = saturate(dot(N, V));
                half fresnel = 0.02 + 0.98 * pow(1.0 - NdotV, 5.0);
                half3 R = reflect(-V, N);
                half3 sky = lerp(_SkyHorizon.rgb, _SkyZenith.rgb, saturate(R.y * 1.6));
                // sun glint
                half3 H = normalize(sun.direction + V);
                half spec = pow(saturate(dot(N, H)), 380.0) * 18.0 + pow(saturate(dot(N, H)), 48.0) * 0.35;
                half shadow = lerp(0.35, 1.0, sun.shadowAttenuation);

                // depth of the water under this pixel
                half depthFade = 1.0;
                half foam = 0.0;
            #if defined(_SD_DEPTH_FOAM)
                float2 suv = i.screenPos.xy / i.screenPos.w;
                float scene = LinearEyeDepth(SampleSceneDepth(suv), _ZBufferParams);
                float water = LinearEyeDepth(i.positionCS.z, _ZBufferParams);
                float thick = max(0.0, scene - water);
                depthFade = saturate(thick / 9.0);
                float edge = 1.0 - saturate(thick / 2.2);
                float foamTex = SD_Noise(pos.xz * 0.35 + t * 0.4) * SD_Noise(pos.xz * 0.9 - t * 0.3);
                foam = saturate(edge * (0.55 + foamTex * 1.3)) * _Foam;
            #endif

                half3 body = lerp(_Shallow.rgb, _Deep.rgb, saturate(0.35 + depthFade * 0.65));
                half3 lit = body * (sun.color * saturate(sun.direction.y) * shadow * 0.55 + SampleSH(half3(0, 1, 0)) * 0.7);
                half3 col = lerp(lit, sky, fresnel) + sun.color * spec * shadow;
                col = lerp(col, half3(0.9, 0.95, 0.97) * (sun.color * 0.6 + 0.35), foam);
                half alpha = lerp(0.55, 1.0, max(fresnel, depthFade));
                alpha = saturate(max(alpha, foam));
                col = MixFog(col, i.fogFactor);
                return half4(col, alpha);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
