using System;
using System.IO;
using RedDust.Meta;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>
    /// Guarda os perfis (carteira, garagem, mochila) em JSON na pasta persistente do jogo. Escrita atómica
    /// (ficheiro temporário + troca) para nunca deixar um perfil meio escrito se o jogo fechar a meio.
    /// </summary>
    public static class ProfileStore
    {
        static string PathFor(string slot) => System.IO.Path.Combine(Application.persistentDataPath, $"profile_{slot}.json");

        public static PlayerProfile Load(string slot, string defaultName)
        {
            string path = PathFor(slot);
            try
            {
                if (File.Exists(path))
                {
                    var p = JsonUtility.FromJson<PlayerProfile>(File.ReadAllText(path));
                    if (p != null)
                    {
                        p.slot = slot;
                        Economy.Sanitize(p);
                        if (Economy.GrantWelcomeKit(p, (ulong)DateTime.UtcNow.Ticks)) Save(p);   // perfis antigos também recebem o kit
                        return p;
                    }
                }
            }
            catch (Exception e) { Debug.LogWarning($"[RDD perfil] {slot} ilegível, a criar novo: {e.Message}"); }
            var fresh = Economy.NewProfile(slot, defaultName, (ulong)DateTime.UtcNow.Ticks ^ Economy.StableHash(slot));
            Economy.GrantWelcomeKit(fresh, (ulong)DateTime.UtcNow.Ticks);
            Save(fresh);
            return fresh;
        }

        public static void Save(PlayerProfile p)
        {
            try
            {
                string path = PathFor(p.slot), tmp = path + ".tmp";
                File.WriteAllText(tmp, JsonUtility.ToJson(p));
                if (!File.Exists(path)) { File.Move(tmp, path); return; }
                try { File.Replace(tmp, path, null); }
                catch (PlatformNotSupportedException) { File.Copy(tmp, path, true); File.Delete(tmp); }
            }
            catch (Exception e) { Debug.LogError($"[RDD perfil] falha a guardar {p.slot}: {e.Message}"); }
        }
    }
}
