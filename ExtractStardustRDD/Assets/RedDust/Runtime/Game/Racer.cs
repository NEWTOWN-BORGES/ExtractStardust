using System.Collections.Generic;
using System.Linq;
using RedDust.Meta;
using RedDust.Track;
using RedDust.Vehicle;
using UnityEngine;

namespace RedDust.Game
{
    /// <summary>
    /// Um piloto na corrida (jogador ou bot): nave, build levada, casco, combustível, calor, consumíveis,
    /// passiva do chassis, estado (RACING/EXTRACTED/DESTROYED/STRANDED/ABANDONED) e progresso.
    /// Os mesmos sistemas valem para jogador e IA (sem batota de velocidade para os bots).
    /// </summary>
    public sealed class Racer
    {
        public string id, name;
        public bool human;
        public int player = -1;                 // 0/1 para os jogadores locais
        public PlayerProfile profile;           // só jogadores
        public ChassisDef chassis;
        public ShipStats stats;
        public VitalsSpec spec;
        public CraftController craft;
        public CraftTuning baseTuning;
        public Color paint;
        public BotBrain brain;
        public PilotInput input;

        // ---- o que leva para a expedição
        public List<EquipmentInstance> carried = new List<EquipmentInstance>();
        public string insured = "";
        public List<ConsumableStack> slots = new List<ConsumableStack>();     // cópia de trabalho do loadout
        public List<ConsumableStack> consumed = new List<ConsumableStack>();
        public int selected;

        // ---- vitais
        public float hull, fuel = 1f, heat;
        public float HullFrac => spec != null ? Mathf.Clamp01(hull / spec.hullMax) : 1f;
        public RaceState state = RaceState.Racing;
        public bool Active => state == RaceState.Racing;
        public bool rules;                      // dano/combustível/calor ativos (não na Exploração)

        // ---- progresso
        public int pathIdx, station;
        public float offTrack;                  // segundos seguidos fora da pista (> 20 m → reposição automática)
        public float raceDistance, finishTime = -1f, endDistance;
        public int position, checkpoint, penalties, repairs, skillRoutes;
        public bool tookDamage, usedBoost;
        readonly HashSet<int> pathsSeen = new HashSet<int>();

        // ---- efeitos e passivas
        sealed class Effect { public ConsumableDef def; public float left; }
        readonly List<Effect> effects = new List<Effect>();
        float trimTimer, razorTimer, longHaulTimer, overdriveHeld, overdriveTimer, strandedTimer, contactTimer, useLock;
        bool longHaul, wasGrounded = true;
        Vector3 commandedVelocity;
        public string alert = "";
        public float alertUntil;
        public List<string> feed;               // notificações para o HUD deste piloto (opcional)

        public float Speed => craft != null ? craft.Speed : 0f;
        public bool Repairing => effects.Any(e => e.def.kind == ConsumableKind.Repair);
        public string PassiveState => chassis.id switch
        {
            "strix" => trimTimer > 0f ? "ADAPTIVE TRIM ativo" : "",
            "wraith" => razorTimer >= 2.5f ? "RAZOR LINE ativo" : "",
            "nomad" => longHaul ? "LONG HAUL ativo" : "",
            "vortex" => overdriveTimer > 0f ? "OVERDRIVE RECOVERY" : "",
            _ => "",
        };

        public void Attach()
        {
            baseTuning = craft.tuning.Clone();
            hull = spec.hullMax;
            craft.Impacted += OnImpact;
            craft.Landed += OnLanded;
        }

        public void Detach()
        {
            if (craft == null) return;
            craft.Impacted -= OnImpact;
            craft.Landed -= OnLanded;
        }

        // ------------------------------------------------------------------ dano

        void OnImpact(float s, Vector3 n, Collider c)
        {
            contactTimer = 0.6f;
            razorTimer = 0f;
            // BASTION — INERTIAL ANCHOR: devolve 25% do deslocamento lateral causado pelo contacto
            if (chassis.id == "bastion" && craft != null)
            {
                Vector3 dv = craft.Body.linearVelocity - commandedVelocity;
                craft.Body.linearVelocity -= 0.25f * Vector3.ProjectOnPlane(dv, craft.Forward);
            }
            if (!rules || !Active) return;
            bool craftHit = c != null && c.gameObject.layer == Layers.Craft;
            float dmg = (s - craft.tuning.impactMin) * 1.1f * spec.impactMul * (craftHit ? 0.6f : 1f);
            Damage(dmg);
            input?.Rumble(Mathf.Min(1f, s / 30f), Mathf.Min(1f, s / 22f), 0.28f);
        }

        void OnLanded(float vn)
        {
            if (chassis.id == "strix") trimTimer = 1.5f;      // ADAPTIVE TRIM depois de uma aterragem
            input?.Rumble(0.25f + vn / 40f, 0.2f + vn / 30f, 0.18f);
            if (!rules || !Active) return;
            if (vn > craft.tuning.landingHard) Damage((vn - craft.tuning.landingHard) * 1.4f * spec.impactMul);
        }

        public void Damage(float amount)
        {
            if (amount <= 0f || !Active) return;
            hull -= amount;
            tookDamage = true;
        }

        // ------------------------------------------------------------------ consumíveis

        public ConsumableStack SlotAt(int i) => i >= 0 && i < slots.Count ? slots[i] : null;

        public string Use(int slotIndex)
        {
            if (!Active || useLock > 0f) return null;
            var s = SlotAt(slotIndex);
            if (s == null || s.count <= 0 || string.IsNullOrEmpty(s.id)) return null;
            var def = Catalog.Consumable(s.id);
            if (def == null) return null;
            s.count--;
            var used = consumed.Find(c => c.id == s.id);
            if (used == null) consumed.Add(new ConsumableStack(s.id, 1)); else used.count++;
            useLock = 0.8f;
            switch (def.kind)
            {
                case ConsumableKind.Surge: craft.AddNitro(def.amount); heat += 12f; break;
                default: effects.Add(new Effect { def = def, left = Mathf.Max(0.1f, def.duration) }); break;
            }
            if (def.kind == ConsumableKind.Repair) repairs++;
            return def.name;
        }

        // ------------------------------------------------------------------ passo fixo

        /// <summary>Antes da física: guarda a velocidade comandada (BASTION) e corre vitais, efeitos e passivas.</summary>
        public void Tick(float dt, float referenceSeconds)
        {
            if (craft == null) return;
            commandedVelocity = craft.Body.linearVelocity;
            var t = craft.tuning; var b = baseTuning;
            t.topSpeed = b.topSpeed; t.stabilityRecover = b.stabilityRecover; t.aeroDrag = b.aeroDrag;
            t.nitroRegen = b.nitroRegen; t.gripLateralMax = b.gripLateralMax; t.alignRate = b.alignRate;
            useLock -= dt; contactTimer -= dt;
            if (craft.Boosting) usedBoost = true;
            if (!Active) return;

            float speedMul = 1f, stabMul = 1f, regenMul = 1f, coolMul = spec.coolMul, effMul = 1f;

            // efeitos dos consumíveis (custo em tempo: reparar abranda a nave)
            for (int i = effects.Count - 1; i >= 0; i--)
            {
                var e = effects[i];
                float step = Mathf.Min(dt, e.left);
                float rate = e.def.amount / Mathf.Max(0.1f, e.def.duration);
                switch (e.def.kind)
                {
                    case ConsumableKind.Repair: hull = Mathf.Min(spec.hullMax, hull + spec.hullMax * rate / 100f * step * spec.repairMul); speedMul *= 1f - e.def.speedPenalty; break;
                    case ConsumableKind.Fuel: fuel = Mathf.Min(1f, fuel + rate * step); break;
                    case ConsumableKind.Coolant: heat = Mathf.Max(0f, heat - rate * step); break;
                    case ConsumableKind.Stabilizer: stabMul *= 1f + e.def.amount; t.gripLateralMax = b.gripLateralMax * 1.08f; break;
                }
                e.left -= dt;
                if (e.left <= 0f) effects.RemoveAt(i);
            }

            // passivas (Doc 02 §4)
            bool grounded = craft.Grounded;
            if (chassis.id == "strix")
            {
                if (wasGrounded && !grounded && craft.SurfaceAngle > 30f) trimTimer = 1.5f;   // saída de parede
                if (trimTimer > 0f) { trimTimer -= dt; stabMul *= 1.2f; }
            }
            else if (chassis.id == "wraith")
            {
                if (grounded && craft.SurfaceAngle > 35f && contactTimer <= 0f) razorTimer += dt; else razorTimer = 0f;
                if (razorTimer >= 2.5f) t.aeroDrag = b.aeroDrag * 0.96f;
            }
            else if (chassis.id == "nomad")
            {
                if (heat < 75f) longHaulTimer += dt; else { longHaulTimer = 0f; longHaul = false; }
                if (longHaulTimer >= 60f) longHaul = true;
                if (longHaul) { effMul *= 0.95f; regenMul *= 1.05f; }
            }
            else if (chassis.id == "vortex")
            {
                if (craft.Boosting) overdriveHeld += dt;
                else { if (overdriveHeld > 2f) overdriveTimer = 3f; overdriveHeld = 0f; }
                if (overdriveTimer > 0f) { overdriveTimer -= dt; coolMul *= 1.2f; regenMul *= 1.15f; }
            }
            wasGrounded = grounded;

            // REDLINE-X: acima de 90% da velocidade máxima, +3% (com mais calor no boost)
            float top = b.topSpeed * speedMul;
            if (spec.redline && craft.Speed > 0.9f * b.topSpeed) top *= 1.03f;
            t.topSpeed = top;
            t.stabilityRecover = b.stabilityRecover * stabMul;
            t.alignRate = b.alignRate * Mathf.Lerp(1f, stabMul, 0.5f);
            t.nitroRegen = b.nitroRegen * regenMul;

            if (!rules) return;

            // calor: o boost aquece, a refrigeração dissipa; a 100 sobreaquece (sem boost e dano contínuo)
            float gain = (craft.Boosting ? 14f * (spec.redline ? 1.15f : 1f) : 0f) * spec.heatGain + (craft.Drifting ? 3f : 0f);
            float loss = 6f * coolMul * (craft.Boosting ? 0.3f : 1f);
            heat = Mathf.Clamp(heat + (gain - loss) * dt, 0f, 120f);
            if (heat >= 100f) Damage(2f * dt);

            // combustível: dimensionado para a duração de referência da pista (Fuel Cell dá margem a quem abusa do boost)
            float throttle = Mathf.Clamp01(craft.input.throttle);
            float use = throttle * (0.55f + 0.45f * Mathf.Clamp01(craft.Speed / b.topSpeed)) * (craft.Boosting ? 2.2f : 1f) * spec.fuelUse * effMul;
            fuel = Mathf.Max(0f, fuel - use * dt / Mathf.Max(60f, referenceSeconds * 0.92f));
            if (fuel <= 0f && craft.Speed < 4f) strandedTimer += dt; else strandedTimer = 0f;

            if (hull <= 0f) { hull = 0f; state = RaceState.Destroyed; }
            else if (strandedTimer > 3f) state = RaceState.Stranded;
        }

        /// <summary>Limites dos vitais sobre o comando (sem combustível não há propulsão; sobreaquecido não há boost).</summary>
        public CraftInput Limit(CraftInput i)
        {
            if (!rules) return i;
            if (fuel <= 0f) { i.throttle = 0f; i.boost = false; }
            if (heat >= 100f) i.boost = false;
            return i;
        }

        public string Alert()
        {
            if (!rules || !Active) return "";
            if (HullFrac <= 0.10f) return "HULL 10%";
            if (heat >= 100f) return "ENGINE CRITICAL · SOBREAQUECIDO";
            if (HullFrac <= 0.25f) return "CASCO CRÍTICO";
            if (fuel <= 0.12f) return "LOW FUEL";
            if (heat >= 85f) return "TEMPERATURA ALTA";
            return "";
        }

        /// <summary>Regista o percurso do grafo em que está (rotas SKILL concluídas contam para contratos).</summary>
        public void NotePath(CourseGraph graph, int path)
        {
            if (path <= 0 || !pathsSeen.Add(path)) return;
            if ((graph.Paths[path].Id ?? "").ToUpperInvariant().Contains("SKILL")) skillRoutes++;
        }

        public void Destroyed()
        {
            if (craft == null) return;
            craft.input = new CraftInput();
            craft.Body.linearVelocity *= 0.3f;
            var vis = craft.transform.Find("Visual");
            if (vis != null)
                foreach (var r in vis.GetComponentsInChildren<Renderer>())
                    if (r.sharedMaterial != null && r.sharedMaterial.HasProperty("_BaseColor"))
                        r.material.SetColor("_BaseColor", r.sharedMaterial.GetColor("_BaseColor") * 0.25f);
        }
    }
}
