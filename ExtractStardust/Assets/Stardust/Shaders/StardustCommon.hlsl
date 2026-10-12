// Shared helpers for the island shaders (terrain, models, water).
#ifndef STARDUST_COMMON_INCLUDED
#define STARDUST_COMMON_INCLUDED

half3 SD_SrgbToLinear(half3 c)
{
    return c * (c * (c * 0.305306011h + 0.682171111h) + 0.012522878h);
}

// normalize that never returns NaN (zero vectors stay zero); NaNs would explode in the bloom
float3 SD_SafeNormalize(float3 v)
{
    return v * rsqrt(max(dot(v, v), 1e-8));
}

float SD_Hash(float2 p)
{
    p = frac(p * float2(123.34, 456.21));
    p += dot(p, p + 45.32);
    return frac(p.x * p.y);
}

// cheap value noise (for macro variation, breaks texture tiling)
float SD_Noise(float2 p)
{
    float2 i = floor(p), f = frac(p);
    float2 u = f * f * (3.0 - 2.0 * f);
    float a = SD_Hash(i), b = SD_Hash(i + float2(1, 0)), c = SD_Hash(i + float2(0, 1)), d = SD_Hash(i + float2(1, 1));
    return lerp(lerp(a, b, u.x), lerp(c, d, u.x), u.y);
}

float SD_Fbm(float2 p)
{
    return SD_Noise(p) * 0.55 + SD_Noise(p * 2.13 + 7.1) * 0.3 + SD_Noise(p * 4.37 - 3.3) * 0.15;
}

// normal stored as plain RGB (OpenGL convention), roughness in alpha
half3 SD_DecodeNormal(half4 t, half strength)
{
    float3 n = t.rgb * 2.0 - 1.0;
    n.xy *= strength;
    n.z = max(n.z, 0.05);
    return SD_SafeNormalize(n);
}

// tangent-space normal for a planar projection whose UV axes are (tu, tv) in world space
half3 SD_ProjectNormal(half3 nTS, half3 nWS, half3 tu, half3 tv)
{
    float3 t = SD_SafeNormalize(tu - nWS * dot(tu, nWS));
    float3 b = SD_SafeNormalize(tv - nWS * dot(tv, nWS) - t * dot(tv, t));
    float3 r = t * nTS.x + b * nTS.y + nWS * nTS.z;
    return dot(r, r) > 1e-6 ? normalize(r) : nWS;
}

#endif
