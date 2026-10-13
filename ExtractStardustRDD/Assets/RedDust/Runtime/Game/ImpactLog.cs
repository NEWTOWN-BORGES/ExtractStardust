using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>Registo de batidas para os autotestes (-rddextract): onde (km), a que velocidade, contra que malha e o dano.</summary>
    public static class ImpactLog
    {
        public static bool On;
        static readonly List<(string who, float km, float speed, string what, float dmg)> items = new List<(string, float, float, string, float)>();

        public static void Add(Racer r, float speed, Collider c, float dmg)
        {
            if (!On || items.Count > 50000) return;
            items.Add((r.name, r.raceDistance / 1000f, speed, c != null ? c.name : "-", dmg));
        }

        public static string Summary()
        {
            var sb = new System.Text.StringBuilder();
            sb.AppendLine($"  Batidas: {items.Count} · dano total {items.Sum(i => i.dmg):0}");
            foreach (var g in items.GroupBy(i => Mathf.FloorToInt(i.km * 4f) / 4f).OrderByDescending(g => g.Sum(i => i.dmg)).Take(12))
                sb.AppendLine($"    {g.Key:0.00} km · {g.Count()} batidas · dano {g.Sum(i => i.dmg):0} · vel. máx {g.Max(i => i.speed):0} m/s · {string.Join(", ", g.GroupBy(i => i.what).OrderByDescending(x => x.Sum(i => i.dmg)).Take(3).Select(x => $"{x.Key}×{x.Count()}"))}");
            return sb.ToString();
        }
    }
}
