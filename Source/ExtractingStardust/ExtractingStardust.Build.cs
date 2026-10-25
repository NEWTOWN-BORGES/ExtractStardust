// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class ExtractingStardust : ModuleRules
{
	public ExtractingStardust(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
	
		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine", "InputCore", "EnhancedInput", "UMG", "Slate", "SlateCore" });

		PrivateDependencyModuleNames.AddRange(new string[] { "ApplicationCore", "InputDevice" });

		if (Target.Platform == UnrealTargetPlatform.Win64)
		{
			// PlayStation pads are read directly over HID (see EXDualShockDevice).
			PublicSystemLibraries.AddRange(new string[] { "hid.lib", "setupapi.lib" });
		}

		// Uncomment if you are using Slate UI
		// PrivateDependencyModuleNames.AddRange(new string[] { "Slate", "SlateCore" });
		
		// Uncomment if you are using online features
		// PrivateDependencyModuleNames.Add("OnlineSubsystem");

		// To include OnlineSubsystemSteam, add it to the plugins section in your uproject file with the Enabled attribute set to true
	}
}
