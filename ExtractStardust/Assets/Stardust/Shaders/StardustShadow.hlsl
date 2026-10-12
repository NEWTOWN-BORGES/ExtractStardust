// Shadow caster pass shared by the island shaders. Define SD_VERTEX_OFFSET + SD_VertexOffset() for animated vertices.
#ifndef STARDUST_SHADOW_INCLUDED
#define STARDUST_SHADOW_INCLUDED

float3 _LightDirection;
float3 _LightPosition;

struct ShadowAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS : NORMAL;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct ShadowVaryings
{
    float4 positionCS : SV_POSITION;
};

ShadowVaryings ShadowVert(ShadowAttributes v)
{
    ShadowVaryings o;
    UNITY_SETUP_INSTANCE_ID(v);
    float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
#ifdef SD_VERTEX_OFFSET
    positionWS = SD_VertexOffset(positionWS, v.positionOS.xyz);
#endif
    float3 normalWS = TransformObjectToWorldNormal(v.normalOS);
#if _CASTING_PUNCTUAL_LIGHT_SHADOW
    float3 lightDirectionWS = normalize(_LightPosition - positionWS);
#else
    float3 lightDirectionWS = _LightDirection;
#endif
    float4 positionCS = TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, lightDirectionWS));
#if UNITY_REVERSED_Z
    positionCS.z = min(positionCS.z, UNITY_NEAR_CLIP_VALUE);
#else
    positionCS.z = max(positionCS.z, UNITY_NEAR_CLIP_VALUE);
#endif
    o.positionCS = positionCS;
    return o;
}

half4 ShadowFrag(ShadowVaryings i) : SV_Target
{
    return 0;
}

#endif
