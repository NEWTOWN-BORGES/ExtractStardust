using System;
using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    public enum Rarity { Common, Uncommon, Rare, Epic, Legendary }
    public enum Slot { Engine, Booster, Stabilizer, Armor, Reactor, Navigator }
    public enum Consumable { RepairGel, FuelCell }

    /// <summary>
    /// A single owned component (GDD 9.2: item_instance_id separate from component_definition_id).
    /// The same instance moves between inventory, reservation, pool and custody — it is never cloned.
    /// </summary>
    [Serializable]
    public class ItemInst
    {
        public string id;      // item_instance_id
        public string defId;   // component_definition_id
        public int slot;
        public int rarity;
        public string name;
        public int serial;     // legendary serial number (0 = none)
        public float roll;     // attribute roll inside the rarity band
        public float roll2;
        public int value;      // estimated CR (catalogue v1), never a wallet balance
        public string origin;
        public string owner;

        public Slot Slot => (Slot)slot;
        public Rarity Rarity => (Rarity)rarity;
        public float Tier => rarity + roll * 0.8f;
        public string DisplayName => serial > 0 ? $"{name} #{serial:000000}" : name;
    }

    public static class Catalog
    {
        public const string Version = "catalogo-demo-1";
        public static readonly int[] RarityValue = { 100, 400, 1200, 2500, 6000 };
        public static readonly string[] RarityName = { "Comum", "Incomum", "Raro", "Épico", "Lendário" };
        public static readonly string[] RarityTag = { "C", "I", "R", "É", "L" };
        public static readonly Color[] RarityColor =
        {
            new Color(0.75f, 0.78f, 0.8f), new Color(0.35f, 0.9f, 0.4f), new Color(0.3f, 0.6f, 1f),
            new Color(0.75f, 0.4f, 1f), new Color(1f, 0.62f, 0.15f)
        };
        public static readonly string[] SlotName = { "Motor", "Propulsor", "Estabilizador", "Blindagem", "Reator", "Navegador" };
        public static readonly string[] ConsumableName = { "Gel de Reparo", "Célula de Combustível" };
        public static readonly int[] ConsumableCost = { 80, 60 };

        static readonly string[][] Families =
        {
            new[] { "Kestrel V4", "Brakk-9", "Halcyon TR", "Solaris Drive", "Ironwake Prime" },
            new[] { "Pulse Jet", "Ember Kick", "Hydra Burst", "Comet Lance", "VORTEX X7" },
            new[] { "Gyra S", "Keel-2", "Talon Fin", "Aegis Trim", "Nightglide" },
            new[] { "Placa M1", "Bulwark", "Carapace", "Hexweave", "Monolith" },
            new[] { "Célula R1", "Fusion Core", "Arc Heart", "Singularity", "Starforge" },
            new[] { "Scout N", "Pathfinder", "Oracle", "Deepsight", "Astrolabe" },
        };

        public static string NewId() => Guid.NewGuid().ToString("N").Substring(0, 16);

        public static ItemInst Create(Slot slot, Rarity r, System.Random rng, string origin, string owner)
        {
            var it = new ItemInst
            {
                id = NewId(),
                slot = (int)slot,
                rarity = (int)r,
                roll = (float)rng.NextDouble(),
                roll2 = (float)rng.NextDouble(),
                origin = origin,
                owner = owner,
            };
            it.defId = $"{slot.ToString().ToLowerInvariant()}_{(int)r}";
            it.name = Families[(int)slot][(int)r];
            if (r == Rarity.Legendary) it.serial = rng.Next(1000, 999999);
            it.value = Mathf.RoundToInt(RarityValue[(int)r] * (0.9f + 0.25f * it.roll) / 10f) * 10;
            return it;
        }

        public static Rarity RollRarity(System.Random rng, float luck = 0f)
        {
            double x = rng.NextDouble() - luck * 0.15;
            if (x < 0.02) return Rarity.Legendary;
            if (x < 0.10) return Rarity.Epic;
            if (x < 0.25) return Rarity.Rare;
            if (x < 0.55) return Rarity.Uncommon;
            return Rarity.Common;
        }

        /// <summary>Short stat description for the garage.</summary>
        public static string Describe(ItemInst it)
        {
            if (it == null) return "-";
            float t = it.Tier;
            switch (it.Slot)
            {
                case Slot.Engine: return $"Vel. máx +{1.2f * t:0.0}%  Acel +{2f * t:0.0}%  Consumo +{3.5f * t:0.0}%";
                case Slot.Booster: return $"Nitro +{2f * t:0.0}%  Gasto nitro -{3f * t:0.0}%";
                case Slot.Stabilizer: return $"Aderência +{6f * t:0.0}%  Resposta +{4f * t:0.0}%";
                case Slot.Armor: return $"Dano -{5f * t:0.0}%  Acel -{1.2f * t:0.0}%";
                case Slot.Reactor: return $"Recarga nitro +{8f * t:0.0}%  Capacidade +{5f * t:0.0}%";
                case Slot.Navigator: return $"Aviso de perigo +{50f * t:0}m";
            }
            return "";
        }

        public static string LegendaryEffect(ItemInst it)
        {
            if (it == null || it.Rarity != Rarity.Legendary) return null;
            int a = Mathf.RoundToInt(10 + it.roll * 10), b = Mathf.RoundToInt(5 + it.roll2 * 6), c = Mathf.RoundToInt(4 + (1 - it.roll) * 4);
            switch (it.Slot)
            {
                case Slot.Engine: return $"Sobrecarga: vel. +{b}%, consumo +{c * 2}%";
                case Slot.Booster: return $"Recuperação energética +{a}%, capacidade +{b}%, estabilidade térmica -{c}%";
                case Slot.Stabilizer: return $"Giro vetorial: aderência +{a}%, nitro -{c}%";
                case Slot.Armor: return $"Casco reativo: dano -{a}%, vel. máx -{c / 2 + 1}%";
                case Slot.Reactor: return $"Núcleo estelar: recarga +{a}%, combustível -{c}%";
                case Slot.Navigator: return $"Leitura profunda: aviso +{a * 10}m";
            }
            return null;
        }
    }

    public struct ShipStats
    {
        public float topSpeed, accel, grip, lateralMax, lateralAccel;
        public float boostMult, boostDrain, nitroCap, nitroRegen;
        public float armor, fuelUse, fuelCap, warnDist;

        public static ShipStats Base => new ShipStats
        {
            topSpeed = 68f, accel = 24f, grip = 3.6f, lateralMax = 24f, lateralAccel = 40f,
            boostMult = 1.32f, boostDrain = 30f, nitroCap = 100f, nitroRegen = 11f,
            armor = 1f, fuelUse = 1f, fuelCap = 100f, warnDist = 220f,
        };

        public static ShipStats From(ItemInst[] equip)
        {
            var s = Base;
            if (equip == null) return s;
            foreach (var it in equip)
            {
                if (it == null) continue;
                float t = it.Tier;
                switch (it.Slot)
                {
                    case Slot.Engine: s.topSpeed *= 1f + 0.012f * t; s.accel *= 1f + 0.02f * t; s.fuelUse *= 1f + 0.035f * t; break;
                    case Slot.Booster: s.boostMult += 0.02f * t; s.boostDrain *= 1f - 0.03f * t; break;
                    case Slot.Stabilizer: s.grip *= 1f + 0.06f * t; s.lateralAccel *= 1f + 0.04f * t; break;
                    case Slot.Armor: s.armor *= 1f - 0.05f * t; s.accel *= 1f - 0.012f * t; break;
                    case Slot.Reactor: s.nitroRegen *= 1f + 0.08f * t; s.nitroCap *= 1f + 0.05f * t; break;
                    case Slot.Navigator: s.warnDist += 50f * t; break;
                }
                if (it.Rarity == Rarity.Legendary)
                {
                    float a = (10 + it.roll * 10) / 100f, b = (5 + it.roll2 * 6) / 100f, c = (4 + (1 - it.roll) * 4) / 100f;
                    switch (it.Slot)
                    {
                        case Slot.Engine: s.topSpeed *= 1f + b; s.fuelUse *= 1f + 2f * c; break;
                        case Slot.Booster: s.nitroRegen *= 1f + a; s.nitroCap *= 1f + b; s.boostDrain *= 1f + c; break;
                        case Slot.Stabilizer: s.grip *= 1f + a; s.nitroRegen *= 1f - c; break;
                        case Slot.Armor: s.armor *= 1f - a; s.topSpeed *= 1f - (c * 0.5f + 0.01f); break;
                        case Slot.Reactor: s.nitroRegen *= 1f + a; s.fuelCap *= 1f - c; break;
                        case Slot.Navigator: s.warnDist += a * 1000f; break;
                    }
                }
            }
            return s;
        }
    }

    [Serializable]
    public class SaveData
    {
        public int version = 1;
        public List<ItemInst> inventory = new List<ItemInst>();
        public List<string> equipped = new List<string>();   // one id per Slot
        public List<ItemInst> custody = new List<ItemInst>(); // inbox when something could not be delivered
        public string insuredId = "";
        public int credits = 1500;
        public int xp;
        public int races, extractions, wins, destroyed;
        public int consA = 0, consB = 1;
        public List<string> medals = new List<string>();
        public List<string> history = new List<string>();
        public float bestTime;

        public ItemInst Find(string id)
        {
            if (string.IsNullOrEmpty(id)) return null;
            foreach (var it in inventory) if (it.id == id) return it;
            return null;
        }

        public ItemInst Equipped(Slot s)
        {
            while (equipped.Count < 6) equipped.Add("");
            return Find(equipped[(int)s]);
        }

        public ItemInst[] EquippedArray()
        {
            var a = new ItemInst[6];
            for (int i = 0; i < 6; i++) a[i] = Equipped((Slot)i);
            return a;
        }

        public List<ItemInst> OfSlot(Slot s)
        {
            var l = new List<ItemInst>();
            foreach (var it in inventory) if (it.Slot == s) l.Add(it);
            l.Sort((a, b) => b.rarity != a.rarity ? b.rarity.CompareTo(a.rarity) : b.value.CompareTo(a.value));
            return l;
        }

        /// <summary>Entry protection (GDD 12.3): every empty slot receives a free standard common part.</summary>
        public int EnsureBaseKit()
        {
            int granted = 0;
            var rng = new System.Random(Environment.TickCount);
            while (equipped.Count < 6) equipped.Add("");
            for (int i = 0; i < 6; i++)
            {
                if (Find(equipped[i]) != null) continue;
                var list = OfSlot((Slot)i);
                if (list.Count > 0) { equipped[i] = list[0].id; continue; }
                var it = Catalog.Create((Slot)i, Rarity.Common, rng, "Proteção base", "player");
                it.name = "Padrão " + Catalog.SlotName[i];
                inventory.Add(it);
                equipped[i] = it.id;
                granted++;
            }
            if (Find(insuredId) == null) insuredId = "";
            return granted;
        }
    }

    public static class SaveSystem
    {
        /// <summary>Automated tests write to their own file so they never touch the player's progress.</summary>
        public static bool TestMode;
        static string FilePath => System.IO.Path.Combine(Application.persistentDataPath, TestMode ? "stardust_save_test.json" : "stardust_save.json");
        public static SaveData Current;

        public static SaveData Load()
        {
            try
            {
                if (System.IO.File.Exists(FilePath))
                {
                    var d = JsonUtility.FromJson<SaveData>(System.IO.File.ReadAllText(FilePath));
                    if (d != null && d.inventory != null) { Current = d; d.EnsureBaseKit(); return d; }
                }
            }
            catch (Exception e) { Debug.LogWarning("Save corrompido, a criar novo: " + e.Message); }
            Current = NewGame();
            Save();
            return Current;
        }

        public static void Save()
        {
            if (Current == null) return;
            try
            {
                var tmp = FilePath + ".tmp";
                System.IO.File.WriteAllText(tmp, JsonUtility.ToJson(Current, true));
                if (System.IO.File.Exists(FilePath)) System.IO.File.Delete(FilePath);
                System.IO.File.Move(tmp, FilePath);
            }
            catch (Exception e) { Debug.LogWarning("Falha ao gravar: " + e.Message); }
        }

        public static SaveData NewGame()
        {
            var d = new SaveData();
            var rng = new System.Random(12345);
            for (int i = 0; i < 6; i++)
            {
                var it = Catalog.Create((Slot)i, Rarity.Common, rng, "Kit inicial", "player");
                d.inventory.Add(it);
                d.equipped.Add(it.id);
            }
            // a few spare parts so the insurance choice matters from the first race
            d.inventory.Add(Catalog.Create(Slot.Booster, Rarity.Uncommon, rng, "Kit inicial", "player"));
            d.inventory.Add(Catalog.Create(Slot.Stabilizer, Rarity.Rare, rng, "Patrocínio Stardust Port", "player"));
            d.inventory.Add(Catalog.Create(Slot.Engine, Rarity.Uncommon, rng, "Kit inicial", "player"));
            return d;
        }

        public static void Reset()
        {
            Current = NewGame();
            Save();
        }
    }
}
