using RedDust.Presentation;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace RedDust.Game
{
    /// <summary>
    /// Em cada pista carregada, troca o diretor do laboratório (SandboxDirector) pelo GameDirector com os modos de jogo,
    /// sem editar as cenas geradas. O laboratório antigo continua disponível para os testes automáticos
    /// (-rddtest, -rddsmoke) e com -rddlab.
    /// </summary>
    public static class GameBoot
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        static void Init()
        {
            SceneManager.sceneLoaded -= OnLoaded;
            SceneManager.sceneLoaded += OnLoaded;
        }

        static void OnLoaded(Scene scene, LoadSceneMode mode)
        {
            if (CommandLine.Has("-rddtest") || CommandLine.Has("-rddsmoke") || CommandLine.Has("-rddlab")) return;
            var lab = Object.FindFirstObjectByType<SandboxDirector>();
            if (lab == null || lab.GetComponent<GameDirector>() != null) return;
            lab.enabled = false;                  // o Start do laboratório já não corre (sceneLoaded vem antes do Start)
            var game = lab.gameObject.AddComponent<GameDirector>();
            game.sun = lab.sun;
            Object.Destroy(lab);
        }
    }
}
