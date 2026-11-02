#pragma once

#include "CoreMinimal.h"
#include "Components/MaterialBillboardComponent.h"
#include "Materials/MaterialInstanceDynamic.h"

/**
 * Cheap flipbook sprites (player, 2026-11-02: "cuidado com as quedas de fps"). A UMaterialBillboardComponent's size
 * lives in its render state: changing it every frame rebuilds that state, and with a few hundred sprites alive (a blast,
 * burning pieces, their trails and smoke) that is what costs. So the square grows in steps of a quarter and, in between,
 * the picture grows inside it (M_FX_Flipbook's Zoom): a rebuild every few tenths of a second instead of every frame.
 */
namespace EXFx
{
	/** Sets a sprite's size (cm). Quad is the size of its square now (0 when it has none yet); keep it with the sprite. */
	inline void SetSpriteSize(UMaterialBillboardComponent* Sprite, UMaterialInstanceDynamic* Material, float& Quad, float Size)
	{
		static const FName ZoomParam(TEXT("Zoom"));
		Size = FMath::Max(Size, 1.0f);
		if (Quad <= 0.0f || Size > Quad || Size < Quad * 0.55f)
		{
			Quad = Size * 1.25f;
			if (Sprite->Elements.Num() > 0)
			{
				Sprite->Elements[0].BaseSizeX = Quad;
				Sprite->Elements[0].BaseSizeY = Quad;
				Sprite->MarkRenderStateDirty();
			}
		}
		Material->SetScalarParameterValue(ZoomParam, Size / Quad);
	}
}
