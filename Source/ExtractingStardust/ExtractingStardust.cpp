// Copyright Epic Games, Inc. All Rights Reserved.

#include "ExtractingStardust.h"
#include "Features/IModularFeatures.h"
#include "IInputDeviceModule.h"
#include "Input/EXDualShockDevice.h"
#include "Modules/ModuleManager.h"

/** Game module. It also registers the PlayStation pad reader as an input device. */
class FExtractingStardustModule : public IInputDeviceModule
{
public:
	using IInputDeviceModule::CreateInputDevice;

	virtual TSharedPtr<IInputDevice> CreateInputDevice(const TSharedRef<FGenericApplicationMessageHandler>& InMessageHandler) override
	{
#if PLATFORM_WINDOWS
		return MakeShared<FEXDualShockDevice>(InMessageHandler);
#else
		return nullptr;
#endif
	}

	virtual void ShutdownModule() override
	{
		IModularFeatures::Get().UnregisterModularFeature(GetModularFeatureName(), this);
	}

	virtual bool IsGameModule() const override
	{
		return true;
	}
};

IMPLEMENT_PRIMARY_GAME_MODULE(FExtractingStardustModule, ExtractingStardust, "ExtractingStardust");
