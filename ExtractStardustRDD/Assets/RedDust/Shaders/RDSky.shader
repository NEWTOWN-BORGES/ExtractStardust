// EXTRACT: STARDUST — céu do deserto: gradiente que encontra a névoa no horizonte, sol com halo quente, cumulus,
// silhuetas de mesas e uma cordilheira distante com neve (inspirada nas La Sal das referências NPS) e um planeta
// gigante gasoso (mundo fictício). Tudo procedural; as cores da névoa vêm de EnvironmentRig (_RD_Fog*).
Shader "RedDust/Sky"
{
    Properties
    {
        _Zenith ("Zénite", Color) = (0.2, 0.38, 0.72, 1)
        _Exposure ("Exposição", Float) = 1
        _SunSize ("Tamanho do sol", Range(0.0002, 0.01)) = 0.0007
        _Clouds ("Cobertura de nuvens", Range(0, 1)) = 0.32
        _PlanetDir ("Direção do planeta", Vector) = (-0.5, 0.36, -0.79, 0)
        _PlanetSize ("Raio angular do planeta (rad)", Range(0.02, 0.3)) = 0.12
        _RangeDir ("Azimute da cordilheira (rad)", Float) = 2.3
        _RangeWidth ("Largura da cordilheira (rad)", Float) = 1.1
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
            #include "RDGeology.hlsl"

            CBUFFER_START(UnityPerMaterial)
                float4 _Zenith;
                float _Exposure, _SunSize, _Clouds, _PlanetSize, _RangeDir, _RangeWidth;
                float4 _PlanetDir;
            CBUFFER_END
            float4 _RD_SunDir;

            struct Attributes { float4 positionOS : POSITION; };
            struct Varyings { float4 positionCS : SV_POSITION; float3 dir : TEXCOORD0; };

            Varyings vert(Attributes v)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
                o.dir = v.positionOS.xyz;
                return o;
            }

            float ridge1(float x, float seed)
            {
                float s = 0.0, a = 0.5;
                for (int k = 0; k < 5; k++)
                {
                    float n = rd_noise(float3(x, seed + k * 7.1, 0.5));
                    s += a * (1.0 - abs(n * 2.0 - 1.0));
                    x *= 2.1; a *= 0.5;
                }
                return s;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float3 d = normalize(i.dir);
                float3 sun = normalize(_RD_SunDir.xyz);
                float y = d.y;
                float mu = dot(d, sun);
                float3 horizon = _RD_FogColor.rgb;

                // corpo do céu
                float3 sky = lerp(horizon, _Zenith.rgb, pow(saturate(y), 0.62));
                sky += _RD_FogSun.rgb * (pow(saturate(mu), 6.0) * 0.32 + pow(saturate(mu), 64.0) * 0.6) * (1.0 - 0.5 * saturate(y));
                float3 groundHaze = lerp(_RD_FogShadow.rgb, horizon, 0.55);

                // nuvens (cumulus num plano alto)
                float cover = 0.0;
                if (y > 0.015)
                {
                    float2 uv = d.xz / (y + 0.12) * 0.55;
                    float t = _Time.y * 0.004;
                    float3 p = float3(uv.x + t, 0.0, uv.y);
                    float n = rd_fbm(p * 1.6, 4);
                    float cumulus = smoothstep(1.0 - _Clouds, 1.0 - _Clouds + 0.25, n);
                    cover = cumulus * smoothstep(0.015, 0.14, y);
                    float shade = rd_fbm(p * 1.6 + float3(sun.x, 0, sun.z) * 0.08, 4);
                    float lit = saturate(0.6 + (n - shade) * 3.5);
                    float3 cloudCol = lerp(lerp(_Zenith.rgb, horizon, 0.5) * 0.9, _RD_FogSun.rgb * 1.25 + 0.15, lit);
                    cloudCol = lerp(cloudCol, horizon * 1.05, (1.0 - saturate(y * 3.0)) * 0.6);
                    sky = lerp(sky, cloudCol, cover * 0.9);
                }

                // planeta gigante gasoso (atrás da atmosfera)
                float3 P = normalize(_PlanetDir.xyz);
                float cp = dot(d, P);
                float ang = acos(clamp(cp, -1.0, 1.0));
                if (ang < _PlanetSize * 1.15)
                {
                    float3 ax = normalize(cross(P, float3(0.15, 1.0, 0.05)));
                    float3 ay = cross(ax, P);
                    float3 q = d - P * cp;
                    float2 uvp = float2(dot(q, ax), dot(q, ay)) / sin(_PlanetSize);
                    float r2 = dot(uvp, uvp);
                    float3 halo = _RD_FogSun.rgb * 0.08 * smoothstep(1.15, 1.0, sqrt(r2));
                    if (r2 < 1.0)
                    {
                        float3 nl = float3(uvp, sqrt(1.0 - r2));
                        float3 nw = normalize(ax * nl.x + ay * nl.y + P * nl.z);
                        float lat = nl.y * 0.93 + nl.x * 0.37;                // eixo inclinado
                        float bands = rd_noise(float3(lat * 9.0, 1.3, 0.0)) * 0.6 + rd_noise(float3(lat * 31.0 + nl.x * 0.6, 2.7, 0.0)) * 0.4;
                        float3 pc = lerp(float3(0.62, 0.48, 0.36), float3(0.86, 0.76, 0.62), bands);
                        pc = lerp(pc, float3(0.48, 0.55, 0.62), smoothstep(0.55, 0.8, rd_noise(float3(lat * 4.0, 5.1, 0.0))) * 0.5);
                        float lightP = saturate(dot(nw, sun) * 0.9 + 0.1);
                        float rim = pow(1.0 - nl.z, 3.0);
                        float3 planet = pc * lightP + float3(0.55, 0.62, 0.75) * rim * 0.25 * saturate(dot(nw, sun) + 0.4);
                        float vis = 0.88 * smoothstep(0.0, 0.12, y);
                        sky = lerp(sky, planet * 1.1, vis * (1.0 - cover));
                    }
                    else sky += halo * smoothstep(0.0, 0.1, y);
                }

                // disco solar
                float disk = smoothstep(1.0 - _SunSize * 1.2, 1.0 - _SunSize, mu);
                sky += _RD_FogSun.rgb * disk * 9.0 * (1.0 - cover * 0.95) * step(0.0, y);

                // horizonte: silhuetas de mesas a toda a volta + cordilheira com neve num setor
                float az = atan2(d.x, d.z);
                float mesas = 0.006 + 0.012 * floor(ridge1(az * 2.4, 3.0) * 3.0) / 3.0 + 0.004 * rd_noise(float3(az * 40.0, 1, 1));
                float dAz = abs(atan2(sin(az - _RangeDir), cos(az - _RangeDir)));
                float sector = smoothstep(_RangeWidth, _RangeWidth * 0.35, dAz);
                float peaks = sector * (0.022 + 0.05 * pow(ridge1(az * 5.0, 11.0), 2.2));
                float h = max(mesas, peaks);
                if (y < h)
                {
                    bool isRange = peaks > mesas;
                    float rel = saturate(y / max(h, 1e-4));
                    float3 far = isRange ? lerp(_RD_FogShadow.rgb * 0.95, horizon, 0.45) : lerp(groundHaze, horizon, 0.35);
                    float slope = ridge1(az * 5.0 + 0.01, 11.0) - ridge1(az * 5.0 - 0.01, 11.0);
                    float sunSide = saturate(0.5 + slope * 6.0 * sign(dot(float2(sun.x, sun.z), float2(cos(az), -sin(az)))));
                    float3 m = far * lerp(0.82, 1.08, sunSide);
                    if (isRange)
                    {
                        float snow = smoothstep(0.62, 0.78, rel + rd_noise(float3(az * 60.0, y * 300.0, 0.0)) * 0.2) * smoothstep(0.03, 0.05, h);
                        m = lerp(m, lerp(float3(0.82, 0.86, 0.95), horizon, 0.35), snow);
                    }
                    sky = lerp(m, horizon, (1.0 - rel) * 0.25);
                }
                if (y < 0.0) sky = lerp(sky, groundHaze, smoothstep(0.0, -0.05, y));
                return half4(sky * _Exposure, 1);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
