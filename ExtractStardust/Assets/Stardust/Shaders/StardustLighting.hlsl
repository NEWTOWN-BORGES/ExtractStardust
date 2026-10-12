// PBR shading of the island (include after URP Lighting.hlsl). Same BRDF as UniversalFragmentPBR, but the sun is
// always applied: with the Forward+ renderer the per-object main light data of terrain/instanced draws is not
// set (distanceAttenuation 0 -> no sunlight) unless the shader declares the cluster keywords.
#ifndef STARDUST_LIGHTING_INCLUDED
#define STARDUST_LIGHTING_INCLUDED

struct SDSurface
{
    half3 albedo;
    half metallic;
    half smoothness;
    half occlusion;
    half3 emission;
};

half3 SD_ShadePBR(InputData input, SDSurface s, out Light sun)
{
    BRDFData brdf;
    half alpha = 1;
    InitializeBRDFData(s.albedo, s.metallic, half3(0, 0, 0), s.smoothness, alpha, brdf);
    sun = GetMainLight(input.shadowCoord, input.positionWS, half4(1, 1, 1, 1));
    sun.distanceAttenuation = 1;
    half occlusion = s.occlusion;
#if defined(_SCREEN_SPACE_OCCLUSION)
    AmbientOcclusionFactor ao = GetScreenSpaceAmbientOcclusion(input.normalizedScreenSpaceUV);
    sun.color *= ao.directAmbientOcclusion;
    occlusion = min(occlusion, ao.indirectAmbientOcclusion);
#endif
    half3 gi = GlobalIllumination(brdf, input.bakedGI, occlusion, input.normalWS, input.viewDirectionWS);
    half3 direct = LightingPhysicallyBased(brdf, sun, input.normalWS, input.viewDirectionWS);
    return gi + direct + s.emission;
}

#endif
