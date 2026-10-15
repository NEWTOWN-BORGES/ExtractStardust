using System;
using System.Collections.Generic;
using System.Linq;

namespace RedDust.Meta
{
    /// <summary>Socket funcional de um chassis: família aceite e classes de tamanho compatíveis (Doc 02 §3, §12).</summary>
    public sealed class SocketDef
    {
        public string id;
        public Family family;
        public SizeClass[] sizes;
        public bool Accepts(EquipmentDef d) => d != null && d.family == family && Array.IndexOf(sizes, d.size) >= 0;
    }

    public sealed class ChassisDef
    {
        public string id, name, role, fantasy, passive, passiveText, weakness;
        public int[] stats;           // 8 stats core do Doc 02 §2
        public float massKg;
        public float hullX, hullY, hullZ; // envelope físico (m): vem dos dados, nunca do mesh
        public uint paint;
        public SocketDef[] sockets;
        public int Base(Stat s) => (int)s < StatInfo.CoreCount ? stats[(int)s] : 0;
        public SocketDef Socket(string id) => Array.Find(sockets, s => s.id == id);
    }

    /// <summary>Stat permitido num módulo, com teto por item (cap da família) e peso de preferência do modelo.</summary>
    public struct StatRule
    {
        public Stat stat; public int cap; public float weight;
        public StatRule(Stat s, int cap, float weight = 1f) { stat = s; this.cap = cap; this.weight = weight; }
    }

    public sealed class EquipmentDef
    {
        public string id, name, manufacturer, desc;
        public Family family;
        public SizeClass size;
        public float massKg;              // massa base do módulo (sempre declarada, Doc 02 §10)
        public StatRule[] stats;          // benefícios permitidos (família) com caps
        public StatRule[] drawbacks;      // stats que podem pagar ganhos extremos (devolvem budget)
        public string visual;             // variante visual (ShipVisuals)
        public bool legendary;
        public string perk, perkText, serialPrefix;
        public StatRoll[] fixedRolls;     // lendários: rolls controlados
        public Rarity MaxRarity => legendary ? Rarity.Legendary : Rarity.Epic;
    }

    public enum ConsumableKind { Repair, Fuel, Coolant, Surge, Stabilizer }

    public sealed class ConsumableDef
    {
        public string id, name, desc;
        public ConsumableKind kind;
        public int price;
        public float amount;        // hull (%), combustível (fração), calor, nitro (fração)
        public float duration;      // s de aplicação
        public float speedPenalty;  // fração de velocidade máxima perdida durante a aplicação (custo em tempo)
    }

    /// <summary>
    /// Conteúdo da demo (Doc 02 §13 e Doc 03 §6): 5 chassis, 31 componentes (28 do documento + 3 kits de propulsão,
    /// família que tem slot próprio mas não tinha contagem), 3 lendários e 6 consumíveis. Valores = TARGETS DE TUNING.
    /// </summary>
    public static class Catalog
    {
        public static readonly ChassisDef[] Chassis;
        public static readonly EquipmentDef[] Equipment;
        public static readonly ConsumableDef[] Consumables;
        static readonly Dictionary<string, ChassisDef> chassisById;
        static readonly Dictionary<string, EquipmentDef> equipById;
        static readonly Dictionary<string, ConsumableDef> consById;

        public static ChassisDef ChassisOf(string id) => id != null && chassisById.TryGetValue(id, out var c) ? c : Chassis[0];
        public static EquipmentDef Def(string id) => id != null && equipById.TryGetValue(id, out var d) ? d : null;
        public static ConsumableDef Consumable(string id) => id != null && consById.TryGetValue(id, out var c) ? c : null;
        public static IEnumerable<EquipmentDef> Regular => Equipment.Where(e => !e.legendary);
        public static IEnumerable<EquipmentDef> Legendaries => Equipment.Where(e => e.legendary);

        // ---- regras por família (Doc 02 §6-7): o que cada família pode dar e com que teto por item
        public static StatRule[] FamilyStats(Family f) => f switch
        {
            Family.Engine => new[] { R(Stat.Speed, 9), R(Stat.Accel, 8), R(Stat.Efficiency, 6) },
            Family.Propulsion => new[] { R(Stat.Boost, 9), R(Stat.Accel, 7), R(Stat.Efficiency, 4) },
            Family.Wings => new[] { R(Stat.Handling, 9), R(Stat.Stability, 9) },
            Family.Tail => new[] { R(Stat.Handling, 6), R(Stat.Stability, 7), R(Stat.Cooling, 5) },
            Family.Armor => new[] { R(Stat.Hull, 14), R(Stat.Cooling, 4) },
            Family.Reactor => new[] { R(Stat.Boost, 10), R(Stat.Efficiency, 4) },
            Family.Cooling => new[] { R(Stat.Cooling, 12), R(Stat.Repair, 8) },
            _ => new[] { R(Stat.Intel, 10), R(Stat.Repair, 5), R(Stat.Efficiency, 3) },
        };

        public static StatRule[] FamilyDrawbacks(Family f) => f switch
        {
            Family.Engine => new[] { R(Stat.Efficiency, 6), R(Stat.Cooling, 6) },
            Family.Propulsion => new[] { R(Stat.Cooling, 6), R(Stat.Efficiency, 5) },
            Family.Wings => new[] { R(Stat.Speed, 3), R(Stat.Accel, 3) },
            Family.Tail => new[] { R(Stat.Speed, 2) },
            Family.Armor => new[] { R(Stat.Accel, 6), R(Stat.Handling, 4) },
            Family.Reactor => new[] { R(Stat.Cooling, 6) },
            Family.Cooling => new[] { R(Stat.Accel, 3) },
            _ => new StatRule[0],
        };

        static StatRule R(Stat s, int cap, float w = 1f) => new StatRule(s, cap, w);
        static readonly SizeClass[] Any = { SizeClass.S, SizeClass.M, SizeClass.L };
        static SocketDef S(string id, Family f, params SizeClass[] sizes) => new SocketDef { id = id, family = f, sizes = sizes.Length == 0 ? Any : sizes };

        static Catalog()
        {
            const SizeClass s = SizeClass.S, m = SizeClass.M, l = SizeClass.L;
            Chassis = new[]
            {
                new ChassisDef { id = "strix", name = "STRIX", role = "Precision All-Rounder", fantasy = "Consigo adaptar-me à corrida sem uma fraqueza destrutiva.",
                    passive = "ADAPTIVE TRIM", passiveText = "Depois de aterrar ou sair de uma parede: +20% de recuperação de estabilidade durante 1,5 s.",
                    weakness = "Não supera as especialistas.", stats = new[] { 72, 74, 76, 75, 66, 66, 68, 70 }, massKg = 1450, hullX = 3.4f, hullY = 1.0f, hullZ = 7.0f, paint = 0xB8150F,
                    sockets = new[] { S("Engine", Family.Engine, m), S("Propulsion", Family.Propulsion, m), S("Wings", Family.Wings, m), S("Armor", Family.Armor, m),
                                      S("Reactor", Family.Reactor, m), S("Cooling", Family.Cooling, m), S("Tail", Family.Tail, m), S("Utility", Family.Utility) } },
                new ChassisDef { id = "wraith", name = "WRAITH", role = "High-Skill Lightweight", fantasy = "Se eu não cometer erros, ganho tempo nas linhas que os outros evitam.",
                    passive = "RAZOR LINE", passiveText = "Bank acima de 35° durante 2,5 s sem contacto: -4% de arrasto enquanto mantiver a linha.",
                    weakness = "Casco e estabilidade baixos.", stats = new[] { 82, 80, 90, 58, 46, 57, 60, 78 }, massKg = 1180, hullX = 2.8f, hullY = 0.9f, hullZ = 7.2f, paint = 0x1C2733,
                    sockets = new[] { S("Engine", Family.Engine, s, m), S("Propulsion", Family.Propulsion, s), S("Wings", Family.Wings, m), S("Armor", Family.Armor, s),
                                      S("Reactor", Family.Reactor, s, m), S("Cooling", Family.Cooling, s), S("Tail", Family.Tail, s), S("Utility", Family.Utility) } },
                new ChassisDef { id = "nomad", name = "NOMAD", role = "Expedition Endurance", fantasy = "Talvez não lidere aos cinco minutos; quero estar eficiente e inteira aos vinte.",
                    passive = "LONG HAUL", passiveText = "60 s abaixo de 75% de temperatura: +5% de eficiência e +5% de recuperação de energia (perde-se ao sobreaquecer).",
                    weakness = "Velocidade e aceleração inferiores.", stats = new[] { 65, 63, 62, 77, 76, 92, 84, 60 }, massKg = 1650, hullX = 3.6f, hullY = 1.1f, hullZ = 7.8f, paint = 0xC9A25A,
                    sockets = new[] { S("Engine", Family.Engine, m, l), S("Propulsion", Family.Propulsion, m), S("Wings", Family.Wings, m, l), S("Armor", Family.Armor, m),
                                      S("Reactor", Family.Reactor, m, l), S("Cooling", Family.Cooling, l), S("Tail", Family.Tail, m, l), S("Utility", Family.Utility), S("Aux", Family.Utility) } },
                new ChassisDef { id = "bastion", name = "BASTION", role = "Heavy Survival", fantasy = "Não preciso evitar tudo; preciso manter a linha e chegar à meta.",
                    passive = "INERTIAL ANCHOR", passiveText = "-25% de deslocamento lateral por contacto e turbulência (não aumenta o dano causado).",
                    weakness = "Manobra e aceleração baixas.", stats = new[] { 61, 54, 52, 92, 96, 65, 73, 55 }, massKg = 1950, hullX = 4.0f, hullY = 1.2f, hullZ = 7.4f, paint = 0x5E6A4C,
                    sockets = new[] { S("Engine", Family.Engine, l), S("Propulsion", Family.Propulsion, l), S("Wings", Family.Wings, l), S("Armor", Family.Armor, l), S("Armor2", Family.Armor, l),
                                      S("Reactor", Family.Reactor, l), S("Cooling", Family.Cooling, l), S("Tail", Family.Tail, l), S("Utility", Family.Utility) } },
                new ChassisDef { id = "vortex", name = "VORTEX", role = "Burst Propulsion", fantasy = "Sou brutal nos momentos certos, mas não posso ficar em overdrive para sempre.",
                    passive = "OVERDRIVE RECOVERY", passiveText = "Depois de mais de 2 s de boost e soltar: 3 s com +20% de refrigeração e +15% de recuperação de energia.",
                    weakness = "Eficiência e refrigeração baixas.", stats = new[] { 75, 91, 68, 65, 61, 49, 55, 96 }, massKg = 1500, hullX = 3.4f, hullY = 1.0f, hullZ = 7.0f, paint = 0x2A55C8,
                    sockets = new[] { S("Engine", Family.Engine, m), S("Propulsion", Family.Propulsion, s, m), S("PropulsionC", Family.Propulsion, s, m), S("Wings", Family.Wings, m),
                                      S("Armor", Family.Armor, s, m), S("Reactor", Family.Reactor, m), S("Cooling", Family.Cooling, m), S("Tail", Family.Tail, m), S("Utility", Family.Utility) } },
            };

            var eq = new List<EquipmentDef>();
            void E(string id, string name, string maker, Family f, SizeClass sz, float mass, string visual, string desc, params (Stat st, float w)[] prefs)
            {
                var rules = FamilyStats(f).Select(r => { foreach (var p in prefs) if (p.st == r.stat) r.weight = p.w; return r; }).ToArray();
                eq.Add(new EquipmentDef { id = id, name = name, manufacturer = maker, family = f, size = sz, massKg = mass, visual = visual, desc = desc, stats = rules, drawbacks = FamilyDrawbacks(f) });
            }
            // motores (6)
            E("eng_vk4", "APEX VK-4 Sprint", "APEX Dynamics", Family.Engine, m, 0, "engine_sprint", "Motor de competição: velocidade de ponta.", (Stat.Speed, 3f));
            E("eng_longstride", "Meridian Longstride", "Meridian Engineering", Family.Engine, m, 20, "engine_endurance", "Consumo baixo para expedições longas.", (Stat.Efficiency, 3f));
            E("eng_hx", "Vanta HX Burner", "Vanta Works", Family.Engine, s, -10, "engine_burner", "Compacto e explosivo à saída das curvas.", (Stat.Accel, 3f));
            E("eng_razor", "APEX Razor-S", "APEX Dynamics", Family.Engine, s, -20, "engine_sprint", "Motor leve para chassis estreitos.", (Stat.Speed, 2f), (Stat.Accel, 1.5f));
            E("eng_ironcore", "Frontier Ironcore", "Frontier Systems", Family.Engine, l, 70, "engine_heavy", "Bloco pesado, potência estável.", (Stat.Accel, 2f), (Stat.Speed, 1.5f));
            E("eng_relic", "Oryx Relic Drive", "Oryx Reclamation", Family.Engine, l, 40, "engine_relic", "Tecnologia recuperada: rápida e frugal.", (Stat.Speed, 2f), (Stat.Efficiency, 2f));
            // propulsão (3)
            E("prop_twin", "APEX Twin Jets", "APEX Dynamics", Family.Propulsion, s, -5, "prop_small", "Impulso afiado, pouca massa.", (Stat.Boost, 2.5f));
            E("prop_vector", "Meridian Vector M", "Meridian Engineering", Family.Propulsion, m, 15, "prop_medium", "Vectoring para saída de curva.", (Stat.Accel, 2f));
            E("prop_heavy", "Frontier Heavy Thrust", "Frontier Systems", Family.Propulsion, l, 60, "prop_large", "Thrusters grandes: força bruta.", (Stat.Boost, 2f), (Stat.Accel, 1.5f));
            // asas / estabilizadores (5)
            E("wing_blade", "APEX Blade Fins", "APEX Dynamics", Family.Wings, s, -10, "wing_short", "Asas curtas: agilidade.", (Stat.Handling, 3f));
            E("wing_long", "Meridian Longspan", "Meridian Engineering", Family.Wings, m, 25, "wing_long", "Estabilizadores longos: banks e aterragens.", (Stat.Stability, 3f));
            E("wing_vector", "Vanta Vector Surfaces", "Vanta Works", Family.Wings, m, 5, "wing_vector", "Superfícies vectoriais para atalhos.", (Stat.Handling, 2f), (Stat.Stability, 1.5f));
            E("wing_brace", "Frontier Brace Wings", "Frontier Systems", Family.Wings, l, 50, "wing_heavy", "Asas reforçadas para wall-ride.", (Stat.Stability, 3f));
            E("wing_glide", "Oryx Glide Array", "Oryx Reclamation", Family.Wings, l, 30, "wing_relic", "Controlo aéreo alienígena.", (Stat.Handling, 2f), (Stat.Stability, 2f));
            // blindagem (4)
            E("arm_skin", "APEX Light Skin", "APEX Dynamics", Family.Armor, s, 30, "armor_light", "Proteção mínima, quase sem massa.", (Stat.Hull, 2f));
            E("arm_guard", "Meridian Guard Plates", "Meridian Engineering", Family.Armor, m, 90, "armor_medium", "Placas modulares fáceis de reparar.", (Stat.Hull, 3f));
            E("arm_plate", "Frontier Bulwark", "Frontier Systems", Family.Armor, l, 180, "armor_heavy", "Painéis grossos e absorvedores.", (Stat.Hull, 4f));
            E("arm_shell", "Oryx Shell Lattice", "Oryx Reclamation", Family.Armor, m, 70, "armor_relic", "Carapaça recuperada com resistência térmica.", (Stat.Hull, 2f), (Stat.Cooling, 1.5f));
            // reatores (4)
            E("rea_spark", "APEX Spark Core", "APEX Dynamics", Family.Reactor, s, 0, "reactor_small", "Recarga rápida de energia.", (Stat.Boost, 3f));
            E("rea_steady", "Meridian Steady Core", "Meridian Engineering", Family.Reactor, m, 20, "reactor_steady", "Energia estável e eficiente.", (Stat.Efficiency, 2f));
            E("rea_flux", "Vanta Flux Reactor", "Vanta Works", Family.Reactor, m, 15, "reactor_flux", "Muita energia, muito calor.", (Stat.Boost, 3f));
            E("rea_titan", "Frontier Titan Core", "Frontier Systems", Family.Reactor, l, 60, "reactor_large", "Reator pesado de grande capacidade.", (Stat.Boost, 2f));
            // refrigeração (3)
            E("cool_vent", "APEX Vent Kit", "APEX Dynamics", Family.Cooling, s, 10, "cooling_vents", "Vents compactos.", (Stat.Cooling, 3f));
            E("cool_radiator", "Meridian Radiator Array", "Meridian Engineering", Family.Cooling, m, 35, "cooling_radiator", "Radiadores grandes e suporte de reparação.", (Stat.Repair, 2f));
            E("cool_grid", "Frontier Heat Grid", "Frontier Systems", Family.Cooling, l, 70, "cooling_grid", "Grelhas térmicas pesadas.", (Stat.Cooling, 3f));
            // caudas (3)
            E("tail_compact", "APEX Compact Tail", "APEX Dynamics", Family.Tail, s, 0, "tail_compact", "Cauda curta: yaw rápido.", (Stat.Handling, 3f));
            E("tail_twin", "Meridian Twin Tail", "Meridian Engineering", Family.Tail, m, 20, "tail_twin", "Cauda dupla estável.", (Stat.Stability, 3f));
            E("tail_long", "Frontier Long Keel", "Frontier Systems", Family.Tail, l, 40, "tail_long", "Quilha longa com vents.", (Stat.Stability, 2f), (Stat.Cooling, 2f));
            // navegação / utilidade (3)
            E("util_scanner", "Meridian Scanner Mast", "Meridian Engineering", Family.Utility, m, 8, "util_mast", "Alertas de perigo mais cedo.", (Stat.Intel, 3f));
            E("util_routeintel", "Oryx Route Oracle", "Oryx Reclamation", Family.Utility, m, 5, "util_dome", "Leitura de rotas e rivais.", (Stat.Intel, 2f), (Stat.Efficiency, 1.5f));
            E("util_drone", "Frontier Field Drone", "Frontier Systems", Family.Utility, m, 15, "util_drone", "Apoio a reparações em corrida.", (Stat.Repair, 3f));

            // lendários (Doc 02 §8): rolls controlados, perk e drawback próprios; nunca vendidos na loja
            eq.Add(new EquipmentDef { id = "leg_helios", name = "HELIOS V-9", manufacturer = "Vanta Works", family = Family.Reactor, size = m, massKg = 20, visual = "reactor_helios",
                legendary = true, serialPrefix = "HV9", perk = "helios", perkText = "Recuperação de energia +17% · capacidade de boost +11% · refrigeração +8 · consumo de combustível +6%",
                desc = "Reator lendário.", stats = FamilyStats(Family.Reactor), drawbacks = FamilyDrawbacks(Family.Reactor),
                fixedRolls = new[] { new StatRoll(Stat.Boost, 14), new StatRoll(Stat.Cooling, 8), new StatRoll(Stat.Efficiency, -6) } });
            eq.Add(new EquipmentDef { id = "leg_redline", name = "REDLINE-X", manufacturer = "APEX Dynamics", family = Family.Engine, size = m, massKg = 10, visual = "engine_redline",
                legendary = true, serialPrefix = "RLX", perk = "redline", perkText = "Acima de 90% da velocidade máxima: +3% de velocidade · calor do boost +15%",
                desc = "Motor lendário de alta potência.", stats = FamilyStats(Family.Engine), drawbacks = FamilyDrawbacks(Family.Engine),
                fixedRolls = new[] { new StatRoll(Stat.Speed, 13), new StatRoll(Stat.Accel, 9), new StatRoll(Stat.Cooling, -5) } });
            eq.Add(new EquipmentDef { id = "leg_aegis", name = "AEGIS FRAME", manufacturer = "Frontier Systems", family = Family.Armor, size = m, massKg = 120, visual = "armor_aegis",
                legendary = true, serialPrefix = "AEG", perk = "aegis", perkText = "Dano de impacto -25% · massa +120 kg",
                desc = "Blindagem lendária de sobrevivência.", stats = FamilyStats(Family.Armor), drawbacks = FamilyDrawbacks(Family.Armor),
                fixedRolls = new[] { new StatRoll(Stat.Hull, 20), new StatRoll(Stat.Cooling, 4), new StatRoll(Stat.Accel, -4) } });
            Equipment = eq.ToArray();

            Consumables = new[]
            {
                new ConsumableDef { id = "coolant", name = "Coolant Cell", kind = ConsumableKind.Coolant, price = 80, amount = 45f, duration = 1.5f, desc = "Reduz a temperatura (-45)." },
                new ConsumableDef { id = "foam", name = "Repair Foam", kind = ConsumableKind.Repair, price = 100, amount = 25f, duration = 8f, speedPenalty = 0.10f, desc = "Reparação lenta e segura (+25% casco em 8 s)." },
                new ConsumableDef { id = "fuel", name = "Fuel Cell", kind = ConsumableKind.Fuel, price = 120, amount = 0.30f, duration = 2f, desc = "+30% de combustível." },
                new ConsumableDef { id = "stab", name = "Stabilizer Shot", kind = ConsumableKind.Stabilizer, price = 140, amount = 0.8f, duration = 8f, desc = "Estabilidade temporária (8 s)." },
                new ConsumableDef { id = "surge", name = "Surge Cell", kind = ConsumableKind.Surge, price = 180, amount = 0.7f, duration = 0f, desc = "+70% de energia de boost imediata (+12 de calor)." },
                new ConsumableDef { id = "nanogel", name = "Rapid Nanogel", kind = ConsumableKind.Repair, price = 220, amount = 35f, duration = 2.5f, speedPenalty = 0.25f, desc = "Reparação rápida (+35% casco em 2,5 s, -25% velocidade)." },
            };

            chassisById = Chassis.ToDictionary(c => c.id);
            equipById = Equipment.ToDictionary(e => e.id);
            consById = Consumables.ToDictionary(c => c.id);
        }
    }
}
