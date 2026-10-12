// Dense grass around the camera (GrassField): blade clusters instanced on the terrain. The vertex shader reads the
// biome and road maps, so grass only grows on grassy ground off the road, and fades in/out at the edge of the ring.
Shader "Stardust/Grass"
{
    Properties
    {
        _Biome ("Biome map", 2D) = "black" {}
        _Roads ("Road mask", 2D) = "black" {}
        _WorldSize ("World size (m)", Float) = 24576
        _Radius ("Visible radius (m)", Float) = 90
        _Wind ("Wind (m)", Float) = 0.18
        _Base ("Base colour", Color) = (0.11, 0.2, 0.05, 1)
        _Tip ("Tip colour", Color) = (0.42, 0.55, 0.18, 1)
        _Dry ("Dry tip colour", Color) = (0.62, 0.55, 0.3, 1)
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        Pass
        {
            Name "ForwardLit"
            Tags { "LightMode"="UniversalForward" }
            Cull Off
            HLSLPROGRAM
            #pragma target 3.5
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_instancing
            #pragma multi_compile _ _MAIN_LIGHT_SHADOWS _MAIN_LIGHT_SHADOWS_CASCADE _MAIN_LIGHT_SHADOWS_SCREEN
            #pragma multi_compile_fragment _ _SHADOWS_SOFT _SHADOWS_SOFT_LOW _SHADOWS_SOFT_MEDIUM _SHADOWS_SOFT_HIGH
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"
            #include "StardustCommon.hlsl"

            TEXTURE2D(_Biome); SAMPLER(sampler_Biome);
            TEXTURE2D(_Roads); SAMPLER(sampler_Roads);
            CBUFFER_START(UnityPerMaterial)
                float _WorldSize, _Radius, _Wind;
                half4 _Base, _Tip, _Dry;
            CBUFFER_END

            struct Attributes { float4 positionOS : POSITION; half4 color : COLOR; UNITY_VERTEX_INPUT_INSTANCE_ID };
            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                float3 positionWS : TEXCOORD0;
                half3 col : TEXCOORD1;
                half h : TEXCOORD2;
                half fog : TEXCOORD3;
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                UNITY_SETUP_INSTANCE_ID(v);
                float3 org = float3(UNITY_MATRIX_M._m03, UNITY_MATRIX_M._m13, UNITY_MATRIX_M._m23);
                float2 uv = org.xz / _WorldSize + 0.5;
                half4 bio = SAMPLE_TEXTURE2D_LOD(_Biome, sampler_Biome, uv, 0);
                half road = SAMPLE_TEXTURE2D_LOD(_Roads, sampler_Roads, uv, 0).r;
                half grassy = saturate(bio.r * 1.3 + bio.g * 0.7 - bio.a * 0.6 - bio.b * 0.4);
                float d = distance(org.xz, _WorldSpaceCameraPos.xz);
                float fade = saturate((_Radius - d) / (_Radius * 0.25));
                float k = saturate(grassy * 1.4 - 0.15) * (1.0 - smoothstep(0.2, 0.5, road)) * fade * step(0.6, org.y);
                float3 p = v.positionOS.xyz;
                p.y *= k;
                p.xz *= lerp(0.6, 1.0, k);
                float3 positionWS = TransformObjectToWorld(p);
                float t = _Time.y;
                float hgt = v.color.a;   // 0 at the root, 1 at the tip
                float s = sin(t * 1.9 + org.x * 0.21 + org.z * 0.17) + 0.4 * sin(t * 4.3 + org.z * 0.5);
                positionWS.xz += float2(s, s * 0.6) * _Wind * hgt * hgt * k;
                o.positionWS = positionWS;
                o.positionCS = TransformWorldToHClip(positionWS);
                half dry = saturate(bio.b + bio.a * 0.5 + (SD_Hash(org.xz) - 0.5) * 0.4);
                half3 tip = lerp(_Tip.rgb, _Dry.rgb, dry * 0.7) * lerp(0.85, 1.15, SD_Hash(org.zx * 1.7));
                o.col = lerp(_Base.rgb, tip, hgt);
                o.h = hgt;
                o.fog = ComputeFogFactor(o.positionCS.z);
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                Light sun = GetMainLight(TransformWorldToShadowCoord(i.positionWS));
                half3 n = half3(0, 1, 0);
                half ndl = saturate(sun.direction.y * 0.6 + 0.4);
                half3 view = GetWorldSpaceNormalizeViewDir(i.positionWS);
                half back = pow(saturate(dot(view, -sun.direction)), 3.0) * i.h;
                half3 lit = i.col * (sun.color * sun.shadowAttenuation * (ndl + back * 0.8) + SampleSH(n) * lerp(0.5, 1.0, i.h));
                lit = MixFog(lit, i.fog);
                return half4(lit, 1);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
