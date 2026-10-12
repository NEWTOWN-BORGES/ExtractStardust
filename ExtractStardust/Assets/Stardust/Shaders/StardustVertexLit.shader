// Cheap lit shader for everything solid: albedo from vertex colour, vertex alpha = 0 marks emissive parts.
// Lambert + hemispheric ambient from global vectors, URP fog. Renders both faces.
Shader "Stardust/VertexLit"
{
    Properties
    {
        _Tint ("Tint", Color) = (1,1,1,1)
        _Lit ("Lighting amount", Range(0,1)) = 1
        _FogAmt ("Fog amount", Range(0,1)) = 1
        _Glow ("Emissive boost", Float) = 1.6
    }
    SubShader
    {
        Tags { "RenderType"="Opaque" "RenderPipeline"="UniversalPipeline" "Queue"="Geometry" }
        LOD 100

        Pass
        {
            Name "Forward"
            Tags { "LightMode"="UniversalForward" }
            Cull Off
            ZWrite On

            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #pragma multi_compile_fog
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            CBUFFER_START(UnityPerMaterial)
                half4 _Tint;
                half _Lit;
                half _FogAmt;
                half _Glow;
            CBUFFER_END

            float4 _SD_SunDir;
            half4 _SD_SunColor;
            half4 _SD_SkyAmb;
            half4 _SD_GroundAmb;

            struct Attributes
            {
                float4 positionOS : POSITION;
                float3 normalOS : NORMAL;
                half4 color : COLOR;
            };

            struct Varyings
            {
                float4 positionCS : SV_POSITION;
                half4 color : COLOR;
                float3 normalWS : TEXCOORD0;
                half fogFactor : TEXCOORD1;
            };

            Varyings vert(Attributes v)
            {
                Varyings o;
                VertexPositionInputs pos = GetVertexPositionInputs(v.positionOS.xyz);
                o.positionCS = pos.positionCS;
                o.normalWS = TransformObjectToWorldNormal(v.normalOS);
                o.color = v.color * _Tint;
                o.fogFactor = ComputeFogFactor(pos.positionCS.z);
                return o;
            }

            half4 frag(Varyings i, FRONT_FACE_TYPE face : FRONT_FACE_SEMANTIC) : SV_Target
            {
                float3 n = normalize(i.normalWS);
                n = IS_FRONT_VFACE(face, n, -n);
                half ndl = saturate(dot(n, normalize(_SD_SunDir.xyz)));
                half3 amb = lerp(_SD_GroundAmb.rgb, _SD_SkyAmb.rgb, n.y * 0.5h + 0.5h);
                half3 light = amb + _SD_SunColor.rgb * ndl;
                light = lerp(half3(1,1,1), light, _Lit);
                half emissive = 1.0h - i.color.a;
                half3 col = i.color.rgb * lerp(light, half3(_Glow, _Glow, _Glow), emissive);
                half3 fogged = MixFog(col, i.fogFactor);
                col = lerp(col, fogged, _FogAmt);
                return half4(col, 1);
            }
            ENDHLSL
        }
    }
    Fallback Off
}
