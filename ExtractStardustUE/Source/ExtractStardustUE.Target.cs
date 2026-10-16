using UnrealBuildTool;
using System.Collections.Generic;

public class ExtractStardustUETarget : TargetRules
{
	public ExtractStardustUETarget(TargetInfo Target) : base(Target)
	{
		Type = TargetType.Game;
		DefaultBuildSettings = BuildSettingsVersion.V7;
		IncludeOrderVersion = EngineIncludeOrderVersion.Unreal5_8;
		ExtraModuleNames.Add("ExtractStardustUE");
	}
}
