// Partícula de efeitos (riscos de velocidade, pó, faíscas, chama do boost): cor do vértice × disco suave
// procedural (sem textura). Mistura configurável: aditiva (SrcAlpha One) ou transparente (SrcAlpha OneMinusSrcAlpha).
Shader "RedDust/FxParticle"
{
    Properties
    {
        [Enum(UnityEngine.Rendering.BlendMode)] _Src ("Src", Float) = 5
        [Enum(UnityEngine.Rendering.BlendMode)] _Dst ("Dst", Float) = 1
        _Soft ("Dureza da borda", Float) = 1.5
    }
    SubShader
    {
        Tags { "RenderType" = "Transparent" "Queue" = "Transparent" "RenderPipeline" = "UniversalPipeline" "IgnoreProjector" = "True" }
        Pass
        {
            Tags { "LightMode" = "UniversalForward" }
            Blend [_Src] [_Dst]
            ZWrite Off
            Cull Off
            HLSLPROGRAM
            #pragma vertex vert
            #pragma fragment frag
            #include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"

            struct Attributes { float4 positionOS : POSITION; half4 color : COLOR; float2 uv : TEXCOORD0; };
            struct Varyings { float4 positionCS : SV_POSITION; half4 color : COLOR; float2 uv : TEXCOORD0; };
            float _Soft;

            Varyings vert(Attributes i)
            {
                Varyings o;
                o.positionCS = TransformObjectToHClip(i.positionOS.xyz);
                o.color = i.color;
                o.uv = i.uv;
                return o;
            }

            half4 frag(Varyings i) : SV_Target
            {
                float2 d = i.uv * 2.0 - 1.0;
                half a = pow(saturate(1.0 - dot(d, d)), _Soft);
                return half4(i.color.rgb, i.color.a * a);
            }
            ENDHLSL
        }
    }
}
