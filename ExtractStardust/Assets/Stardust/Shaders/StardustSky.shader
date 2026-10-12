// Gradient skybox whose horizon equals the fog colour, with a sun glow and two moons.
Shader "Stardust/Sky"
{
    Properties
    {
        _Top ("Zenith", Color) = (0.3, 0.42, 0.62, 1)
        _Horizon ("Horizon (fog)", Color) = (0.9, 0.68, 0.48, 1)
        _SunDir ("Sun direction", Vector) = (0.35, 0.45, 0.82, 0)
        _SunCol ("Sun colour", Color) = (1, 0.9, 0.7, 1)
        _MoonDir ("Moon direction", Vector) = (-0.5, 0.35, 0.8, 0)
        _MoonCol ("Moon colour", Color) = (0.85, 0.82, 0.78, 1)
        _Stars ("Stars", Range(0,1)) = 0
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

            CBUFFER_START(UnityPerMaterial)
                half4 _Top;
                half4 _Horizon;
                float4 _SunDir;
                half4 _SunCol;
                float4 _MoonDir;
                half4 _MoonCol;
                half _Stars;
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

            float hash(float3 p)
            {
                p = frac(p * 0.3183099 + 0.1);
                p *= 17.0;
                return frac(p.x * p.y * p.z * (p.x + p.y + p.z));
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float h = d.y;
                half3 c = lerp(_Horizon.rgb, _Top.rgb, pow(saturate(h), 0.5));
                float sd = saturate(dot(d, normalize(_SunDir.xyz)));
                c += _SunCol.rgb * (pow(sd, 600.0) * 4.0 + pow(sd, 18.0) * 0.25 + pow(sd, 3.0) * 0.06);
                // large moon: soft limb darkening and faint maria, fades near the horizon haze
                float3 md = normalize(_MoonDir.xyz);
                float m = dot(d, md);
                float disc = smoothstep(0.99878, 0.99886, m);
                half limb = 0.72 + 0.28 * smoothstep(0.99878, 0.99960, m);
                half maria = 0.9 + 0.1 * sin(d.x * 900.0) * sin(d.y * 700.0);
                half3 moon = _MoonCol.rgb * limb * maria;
                c = lerp(c, lerp(c, moon, 0.85), disc * saturate(h * 6.0));
                // small second moon
                float3 md2 = normalize(float3(-md.z, md.y * 0.6 + 0.25, md.x));
                float disc2 = smoothstep(0.99955, 0.9996, dot(d, md2));
                c = lerp(c, half3(0.75, 0.55, 0.45), disc2 * saturate(h * 8.0));
                // stars for darker skies
                float3 cell = floor(d * 220.0);
                float st = step(0.9965, hash(cell)) * saturate(h * 3.0) * _Stars;
                c += st;
                return half4(c, 1);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
