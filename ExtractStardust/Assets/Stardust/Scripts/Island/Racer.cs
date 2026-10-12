using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    /// <summary>What the audio needs to know about a ship (engine voices, alarms).</summary>
    public interface IVoiceShip
    {
        Vector3 Pos { get; }
        float Speed01 { get; }
        bool Boosting { get; }
        float Throttle { get; }
        float Scrape { get; }
        bool Repairing { get; }
        bool Alive { get; }
        bool Critical { get; }
        bool IsHuman { get; }
        bool IsRacing { get; }
    }

    /// <summary>One ship in an island race: physics, pilot (human/bot), integrity, fuel, gates and statistics.</summary>
    public class Racer : IVoiceShip
    {
        public int index;
        public Pilot pilot;
        public ShipStats st;
        public readonly Hovercraft craft = new Hovercraft();
        public BotPilot bot;
        public IslandInput input;
        public ShipVisual vis;
        public PilotState state = PilotState.Grid;

        // gameplay
        public float integrity = 100f, fuel = 100f;
        public int nextGate;
        public float finishTime = -1f, destroyTime = -1f;
        public int place;
        public float progress;          // gates passed + fraction (ordering)
        public float respawnT, repairT, invulnT;
        public string destroyCause;
        public float scrape;             // 0..1 for audio/fx
        public float lastBumpT = -9f;
        public float stuckT;
        public float lastGateT;          // race time of the last gate passed (lost bots)
        public bool lostRecover;
        public int[] gateRouteIdx;      // bots: route index of every gate
        public Vector3 stuckP;
        public float safeT;
        public readonly List<(Vector3 pos, float yaw)> safe = new List<(Vector3, float)>();
        public bool lowFuelWarned, criticalWarned;
        public float lowFuelT;

        // ghost mode (bots far from every human: cheap motion along the route, no physics)
        public bool ghost;
        public float ghostSpeed;

        // interpolation
        public Vector3 prevPos;
        public float prevYaw;

        // network (other players on the Wi-Fi)
        public readonly List<LanNet.ShipState> netBuf = new List<LanNet.ShipState>();
        public float netClock;
        public bool netFinishSent;

        // statistics (medals, results)
        public bool tookDamage, usedRepair, usedFuel;
        public float nitroUsedSeconds;
        public float minIntegrity = 100f;
        public int consumedCost;
        public int drifts;
        bool wasDrifting;
        public float distance;
        public readonly List<ItemInst> lost = new List<ItemInst>();

        public bool Active => state == PilotState.Racing || state == PilotState.Respawning;
        public bool Done => state == PilotState.Finished || state == PilotState.Destroyed || state == PilotState.Stranded || state == PilotState.Abandoned;
        public float SpeedKmh => craft.Speed * 3.6f;
        public bool Human => pilot.human;

        public void CountDrift()
        {
            if (craft.drifting && !wasDrifting) drifts++;
            wasDrifting = craft.drifting;
        }

        public Vector3 InterpolatedPos(float alpha) => Vector3.LerpUnclamped(prevPos, craft.position, alpha);
        public float InterpolatedYaw(float alpha) => Mathf.LerpAngle(prevYaw * Mathf.Rad2Deg, craft.yaw * Mathf.Rad2Deg, alpha) * Mathf.Deg2Rad;

        // IVoiceShip
        public Vector3 Pos => craft.position;
        public float Speed01 => Mathf.Clamp01(craft.Speed / 110f);
        public bool Boosting => craft.nitroActive || craft.boost > 4f;
        public float Throttle => craft.running && !craft.input.brake ? 1f : 0.2f;
        public float Scrape => scrape;
        public bool Repairing => repairT > 0f;
        public bool Alive => state == PilotState.Racing || state == PilotState.Finished || state == PilotState.Grid;
        public bool Critical => integrity < 25f && state == PilotState.Racing;
        public bool IsHuman => pilot.human && !pilot.remote;
        public bool IsRacing => state == PilotState.Racing && !ghost;
    }
}
