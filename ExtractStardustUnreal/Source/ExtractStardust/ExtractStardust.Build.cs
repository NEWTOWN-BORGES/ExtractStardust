using UnrealBuildTool;

public class ExtractStardust : ModuleRules
{
	public ExtractStardust(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "InputCore", "PhysicsCore",
			"UMG", "Slate", "SlateCore", "Json", "JsonUtilities"
		});

		string CourseData = "$(ProjectDir)/Content/Stardust/Data/";
		RuntimeDependencies.Add(CourseData + "red_dust_divide_course.bytes", StagedFileType.UFS);
		RuntimeDependencies.Add(CourseData + "sandbox_course.bytes", StagedFileType.UFS);
		RuntimeDependencies.Add(CourseData + "red_dust_divide_graph.bytes", StagedFileType.UFS);
		RuntimeDependencies.Add(CourseData + "red_dust_divide_obstacles.json", StagedFileType.UFS);
		RuntimeDependencies.Add(CourseData + "sandbox_graph.bytes", StagedFileType.UFS);
		RuntimeDependencies.Add(CourseData + "sandbox_obstacles.json", StagedFileType.UFS);
	}
}