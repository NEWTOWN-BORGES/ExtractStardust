// Realistic day sky for the island: zenith/horizon gradient that meets the fog colour, Rayleigh brightening at the
// horizon, sun disk with Mie glow, drifting cumulus/cirrus clouds lit by the sun and a pale moon.
Shader "Stardust/SkyHD"
{
    Properties
    {
        _Zenith ("Zenith", Color) = (0.22, 0.42, 0.74, 1)
        _Horizon ("Horizon (fog)", Color) = (0.68, 0.76, 0.82, 1)
        _Ground ("Below horizon", Color) = (0.45, 0.47, 0.48, 1)
        _SunDir ("Sun direction (to the sun)", Vector) = (0.5, 0.53, 0.7, 0)
        _SunCol ("Sun colour", Color) = (1, 0.9, 0.75, 1)
        _SunSize ("Sun size", Range(0.0002, 0.02)) = 0.0007
        _Exposure ("Exposure", Float) = 1
        _Clouds ("Cloud cover", Range(0, 1)) = 0.45
        _CloudSpeed ("Cloud speed", Float) = 0.004
        _MoonDir ("Moon direction", Vector) = (-0.55, 0.3, 0.78, 0)
        _Quality ("Quality", Float) = 1
    }
    SubShader
    {
        Tags { "Queue"="Background" "RenderType"="Background" "PreviewType"="Skybox" "RenderPipeline"="UniversalPipeline" }
        Cull Off ZWrite Off

        Pass
        {
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "StardustCommon.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Zenith;
                half4 _Horizon;
                half4 _Ground;
                float4 _SunDir;
                half4 _SunCol;
                float _SunSize;
                half _Exposure;
                half _Clouds;
                float _CloudSpeed;
                float4 _MoonDir;
                half _Quality;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 dir : TEXCOORD0; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.dir = v.positionOS.xyz;
                return o;
            }

            float CloudNoise(float2 p)
            {
                float n = SD_Noise(p) * 0.5 + SD_Noise(p * 2.03 + 3.1) * 0.25 + SD_Noise(p * 4.11 - 1.7) * 0.125;
                if (_Quality > 0.5) n += SD_Noise(p * 8.3 + 9.2) * 0.0625;
                return n / 0.9375;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float3 sun = normalize(_SunDir.xyz);
                float h = d.y;
                float up = saturate(h);
                // sky body: zenith -> horizon, brighter and whiter towards the horizon (Rayleigh path length)
                half3 sky = lerp(_Horizon.rgb, _Zenith.rgb, pow(up, 0.45));
                sky += _Horizon.rgb * 0.12 * exp(-up * 9.0);
                float mu = dot(d, sun);
                // Mie glow around the sun, stronger near the horizon
                half3 glow = _SunCol.rgb * (pow(saturate(mu), 8.0) * 0.16 + pow(saturate(mu), 96.0) * 0.4) * lerp(1.0, 0.6, up);
                sky += glow;
                // below the horizon: ground haze
                sky = lerp(sky, _Ground.rgb, smoothstep(0.0, -0.08, h));

                // clouds on a plane above the camera
                half cover = 0;
                [branch] if (h > 0.01 && _Clouds > 0.01)
                {
                    float2 uv = d.xz / (h + 0.08) * 0.6;
                    float t = _Time.y * _CloudSpeed;
                    float n = CloudNoise(uv * 1.3 + float2(t, t * 0.4));
                    float cumulus = smoothstep(1.0 - _Clouds, 1.0 - _Clouds + 0.28, n);
                    float cirrus = smoothstep(0.55, 0.95, SD_Noise(float2(uv.x * 0.6, uv.y * 3.0) + t * 1.7)) * 0.35;
                    cover = saturate(cumulus + cirrus * (1.0 - cumulus)) * smoothstep(0.01, 0.16, h);
                    // light: sunward edges bright, thick cores grey-blue
                    float shade = CloudNoise(uv * 1.3 + float2(t, t * 0.4) + sun.xz * 0.06);
                    half lit = saturate(0.65 + (n - shade) * 3.0);
                    half3 cloudCol = lerp(_Zenith.rgb * 0.55 + _Horizon.rgb * 0.45, _SunCol.rgb * 1.15, lit);
                    cloudCol += _SunCol.rgb * pow(saturate(mu), 12.0) * 0.5;
                    cloudCol = lerp(cloudCol, _Horizon.rgb, (1.0 - up) * 0.55);
                    sky = lerp(sky, cloudCol, cover * 0.92);
                }

                // sun disk (HDR, hidden by clouds)
                float disk = smoothstep(1.0 - _SunSize * 1.15, 1.0 - _SunSize, mu);
                sky += _SunCol.rgb * disk * 7.0 * (1.0 - cover * 0.9) * step(0.0, h);

                // pale daytime moon
                float3 moon = normalize(_MoonDir.xyz);
                float mm = dot(d, moon);
                float md = smoothstep(0.99955, 0.99965, mm);
                half crater = SD_Noise(d.xz * 900.0) * 0.25 + 0.75;
                sky = lerp(sky, half3(0.92, 0.93, 0.95) * crater, md * 0.55 * (1.0 - cover));
                return half4(sky * _Exposure, 1);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
