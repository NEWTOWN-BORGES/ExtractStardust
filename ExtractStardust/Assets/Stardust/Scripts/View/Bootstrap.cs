using UnityEngine;

namespace Stardust
{
    /// <summary>Creates the game object graph at start-up, so the scene itself can stay empty.</summary>
    public static class Bootstrap
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        static void Boot()
        {
            if (IslandTest.Requested)
            {
                var t = new GameObject("IslandTest");
                Object.DontDestroyOnLoad(t);
                t.AddComponent<IslandTest>();
                return;
            }
            if (Object.FindFirstObjectByType<GameApp>() != null) return;
            var go = new GameObject("GameApp");
            Object.DontDestroyOnLoad(go);
            go.AddComponent<GameApp>();
        }
    }
}
