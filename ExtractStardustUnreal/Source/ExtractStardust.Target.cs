using UnrealBuildTool;
using System.Collections.Generic;

public class ExtractStardustTarget : TargetRules
{
	public ExtractStardustTarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V6;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("ExtractStardust");
	}
}
