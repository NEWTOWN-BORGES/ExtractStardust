using UnrealBuildTool;

public class ExtractingStardustEditor : ModuleRules
{
	public ExtractingStardustEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[] { "Core", "CoreUObject", "Engine" });
		PrivateDependencyModuleNames.AddRange(new string[] { "UnrealEd", "Landscape", "RenderCore", "ExtractingStardust" });
	}
}
