// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class ExtractingStardust : ModuleRules
{
	public ExtractingStardust(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		// Many files keep their own constants in anonymous namespaces (CmPerM, ColorParam...): compiled one by one, never
		// merged into unity blobs where the names collide (2026-11-02, after the cloud work came in).
		bUseUnity = false;
	
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "UMG" });

		PrivateDependencyModuleNames.AddRange(new string[] { "ApplicationCore", "InputDevice", "Slate", "SlateCore" });

		if (Target.Platform == UnrealTargetPlatform.Win64)
		{
			// PlayStation pads are read directly over HID (see EXDualShockDevice).
			PublicSystemLibraries.AddRange(new string[] { "hid.lib", "setupapi.lib" });
		}

		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
