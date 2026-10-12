// DepthOnly / DepthNormals passes shared by the island shaders (needed for SSAO and the depth prepass).
#ifndef STARDUST_DEPTH_INCLUDED
#define STARDUST_DEPTH_INCLUDED

struct DepthAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS : NORMAL;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct DepthVaryings
{
    float4 positionCS : SV_POSITION;
    float3 normalWS : TEXCOORD0;
};

DepthVaryings DepthVert(DepthAttributes v)
{
    DepthVaryings o;
    UNITY_SETUP_INSTANCE_ID(v);
    float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
#ifdef SD_VERTEX_OFFSET
    positionWS = SD_VertexOffset(positionWS, v.positionOS.xyz);
#endif
    o.positionCS = TransformWorldToHClip(positionWS);
    o.normalWS = TransformObjectToWorldNormal(v.normalOS);
    return o;
}

DepthVaryings DepthNormalsVert(DepthAttributes v)
{
    return DepthVert(v);
}

half DepthFrag(DepthVaryings i) : SV_Target
{
    return i.positionCS.z;
}

half4 DepthNormalsFrag(DepthVaryings i) : SV_Target
{
    return half4(NormalizeNormalPerPixel(i.normalWS), 0.0);
}

#endif
