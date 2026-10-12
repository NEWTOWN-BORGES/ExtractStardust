using System.Collections.Generic;
using UnityEngine;
using UnityEngine.UI;

namespace Stardust
{
    /// <summary>Wi-Fi lobby and the network side of a race (other players are drawn from their states, no collisions).</summary>
    public partial class GameApp
    {
        public LanNet net;
        bool mpRace;
        float netSendT, lobbyRefresh;
        int lobbyEvent;
        static readonly string[] LobbyEvents = { "expedicao", "floresta", "monumentos", "drag", "explorar" };
        InputField nameField, ipField;
        Text lobbyStatus, lobbyPlayers;
        RectTransform hostList;
        bool searching;
        const float NetDelay = 0.12f;

        void EnsureNet()
        {
            if (net != null) return;
            net = new LanNet { myName = PlayerPrefs.GetString("sd_name", "Piloto " + Random.Range(10, 99)) };
            net.PlayersChanged += () => lobbyRefresh = 0f;
            net.StartRace += (id, seed) => StartNetRace(id, seed);
            net.CountdownGo += () => { if (race != null) race.waitForGo = false; };
            net.PeerState += OnPeerState;
            net.PeerFinished += OnPeerFinished;
            net.BackToMenu += () => { if (state != State.Menu && state != State.Lobby) QuitToMenu(); else ShowLobby(); };
        }

        InputField MakeInput(RectTransform parent, string value, Vector2 anchor, Vector2 pos, Vector2 size)
        {
            var bg = UIKit.PanelAt(parent, "Input", new Color(0.08f, 0.14f, 0.2f, 0.95f), anchor, pos, size);
            bg.raycastTarget = true;
            var text = UIKit.Label(bg.rectTransform, value, 20, TextAnchor.MiddleLeft, Color.white, Vector2.zero, Vector2.one, new Vector2(10, 0), new Vector2(-10, 0), false);
            text.supportRichText = false;
            var f = bg.gameObject.AddComponent<InputField>();
            f.textComponent = text;
            f.text = value;
            f.targetGraphic = bg;
            return f;
        }

        void ShowLobby()
        {
            EnsureNet();
            state = State.Lobby;
            hudLayer.gameObject.SetActive(false);
            var r = NewScreen("Lobby", new Color(0.02f, 0.03f, 0.05f, 0.9f));
            UIKit.LabelAt(r, "MULTIPLAYER WI-FI", 40, TextAnchor.UpperLeft, Color.white, new Vector2(0, 1), new Vector2(60, -34), new Vector2(900, 60));
            UIKit.LabelAt(r, "Todos na mesma rede Wi-Fi (ou ligados ao hotspot de um telemóvel). Um CRIA o jogo, os outros ENTRAM. Até 4 jogadores.",
                16, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(60, -88), new Vector2(1100, 30));
            UIKit.LabelAt(r, "O seu nome", 16, TextAnchor.MiddleLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(60, -134), new Vector2(200, 40));
            nameField = MakeInput(r, net.myName, new Vector2(0, 1), new Vector2(200, -134), new Vector2(300, 44));
            nameField.onEndEdit.AddListener(s => { net.myName = string.IsNullOrWhiteSpace(s) ? net.myName : s.Trim(); PlayerPrefs.SetString("sd_name", net.myName); });
            var buttons = new List<Button>();
            float y = -196f;
            Button B(string label, System.Action a, float x = 60f, float w = 360f)
            {
                var b = UIKit.Button(r, label, () => { Click(); a(); }, new Vector2(0, 1), new Vector2(x, y), new Vector2(w, 52), 19);
                buttons.Add(b);
                return b;
            }
            if (!net.online)
            {
                B("CRIAR JOGO (ANFITRIÃO)", () => { if (net.Host()) ShowLobby(); });
                y -= 62f;
                B(searching ? "A PROCURAR…" : "PROCURAR JOGOS NA REDE", () => { searching = true; net.StartSearch(); ShowLobby(); });
                y -= 62f;
                ipField = MakeInput(r, PlayerPrefs.GetString("sd_lastip", "192.168.1."), new Vector2(0, 1), new Vector2(60, y), new Vector2(230, 52));
                B("ENTRAR POR IP", () => { PlayerPrefs.SetString("sd_lastip", ipField.text); net.Join(ipField.text.Trim()); ShowLobby(); }, 300f, 180f);
                y -= 72f;
                UIKit.LabelAt(r, "JOGOS ENCONTRADOS", 16, TextAnchor.UpperLeft, UIKit.Accent, new Vector2(0, 1), new Vector2(60, y), new Vector2(400, 24));
                hostList = UIKit.Rect(r, "Hosts", new Vector2(0, 1), new Vector2(0, 1), new Vector2(60, y - 260), new Vector2(560, y - 28));
                RefreshHostList();
            }
            else
            {
                if (net.isHost)
                {
                    var evB = B("PROVA: " + EventById(LobbyEvents[lobbyEvent]).name.ToUpperInvariant(), () => { lobbyEvent = (lobbyEvent + 1) % LobbyEvents.Length; ShowLobby(); }, 60f, 520f);
                    y -= 62f;
                    var go = B("COMEÇAR A CORRIDA", () =>
                    {
                        if (net.players.Count < 2) { net.status = "Precisa de pelo menos 2 jogadores (ou jogue sozinho no menu)."; lobbyRefresh = 0f; return; }
                        net.HostStart(LobbyEvents[lobbyEvent], Random.Range(1, 1 << 30));
                    }, 60f, 520f);
                    go.GetComponent<Image>().color = new Color(0.5f, 1f, 0.7f);
                    y -= 62f;
                    var ips = string.Join(", ", LanNet.LocalIPs());
                    UIKit.LabelAt(r, $"O seu endereço: {ips}", 16, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), new Vector2(60, y), new Vector2(700, 26));
                    y -= 34f;
                }
                B("SAIR DO JOGO", () => { LeaveLobby(); ShowLobby(); });
                y -= 70f;
            }
            lobbyPlayers = UIKit.LabelAt(r, "", 20, TextAnchor.UpperLeft, Color.white, new Vector2(1, 1), new Vector2(-560, -140), new Vector2(520, 300));
            lobbyStatus = UIKit.LabelAt(r, net.status, 18, TextAnchor.LowerLeft, UIKit.Warn, new Vector2(0, 0), new Vector2(60, 100), new Vector2(1100, 30));
            var back = UIKit.Button(r, "VOLTAR", () => { Click(); LeaveLobby(); ShowMenu(); }, new Vector2(0, 0), new Vector2(60, 30), new Vector2(240, 54));
            buttons.Add(back);
            RefreshLobbyText();
            Select(buttons[0]);
        }

        void RefreshHostList()
        {
            if (hostList == null) return;
            foreach (Transform c in hostList) Destroy(c.gameObject);
            float y = 0f;
            foreach (var h in net.hosts.Values)
            {
                var ip = h.ip;
                UIKit.Button(hostList, $"{h.name}  ·  {h.count}/{LanNet.MaxPlayers}  ·  {ip}", () => { Click(); net.Join(ip); ShowLobby(); }, new Vector2(0, 1), new Vector2(0, y), new Vector2(500, 46), 17);
                y -= 52f;
            }
            if (net.hosts.Count == 0)
                UIKit.LabelAt(hostList, searching ? "A procurar… (o anfitrião tem de carregar em CRIAR JOGO)" : "Carregue em PROCURAR JOGOS NA REDE.", 15, TextAnchor.UpperLeft, UIKit.Dim, new Vector2(0, 1), Vector2.zero, new Vector2(500, 40));
        }

        void RefreshLobbyText()
        {
            if (lobbyPlayers == null) return;
            var sb = new System.Text.StringBuilder();
            if (net.online)
            {
                sb.AppendLine("<b>JOGADORES</b>");
                foreach (var id in net.SortedIds())
                {
                    var p = net.players[id];
                    sb.AppendLine($"<color=#{UIKit.Hex(LanNet.Colors[p.color % LanNet.Colors.Length])}>■</color> {p.name}{(id == 1 ? "  (anfitrião)" : "")}{(id == net.myId ? "  ← você" : "")}");
                }
                if (!net.isHost) sb.AppendLine("\nÀ espera que o anfitrião comece…");
            }
            lobbyPlayers.text = sb.ToString();
            if (lobbyStatus != null) lobbyStatus.text = net.status;
        }

        void UpdateLobby(float dt)
        {
            net.Poll(dt);
            lobbyRefresh -= dt;
            if (lobbyRefresh <= 0f)
            {
                lobbyRefresh = 0.5f;
                RefreshLobbyText();
                if (!net.online) RefreshHostList();
            }
        }

        void LeaveLobby()
        {
            searching = false;
            net?.Leave();
        }

        // ------------------------------------------------------------------ network race

        void StartNetRace(string eventId, int seed)
        {
            var def = EventById(eventId);
            def.botCount = 0;
            def.economy = false;
            def.rewardScale = Mathf.Min(def.rewardScale, 0.5f);
            StopAllCoroutines();
            ClearRace();
            HideAllScreens();
            currentEvent = def;
            twoPlayers = false;
            mpRace = true;
            var pilots = new List<Pilot>();
            foreach (var id in net.SortedIds())
            {
                var np = net.players[id];
                bool me = id == net.myId;
                var p = me ? MakePlayerPilot() : new Pilot { human = true, remote = true };
                p.name = np.name;
                p.number = id;
                p.livery = LanNet.Colors[np.color % LanNet.Colors.Length];
                p.tag = "net" + id;
                pilots.Add(p);
            }
            raceRoot = new GameObject("Race").transform;
            race = new IslandRace(world, def, pilots, seed) { waitForGo = true };
            humans.Clear();
            foreach (var r in race.racers)
            {
                if (r.pilot.human && !r.pilot.remote)
                {
                    r.input = new IslandInput(0);
                    humans.Add(r);
                }
                r.vis = ShipVisual.Create(raceRoot, r.pilot.model, r.pilot.livery, quality, true);
            }
            FinishRaceSetup(def);
            foreach (var h in huds) h.Message(def.name.ToUpperInvariant(), "À espera dos outros jogadores…", 30f);
            net.ReportReady();
        }

        void OnPeerState(LanNet.ShipState s)
        {
            if (race == null || !mpRace) return;
            foreach (var r in race.racers)
            {
                if (!r.pilot.remote || r.pilot.number != s.id) continue;
                if (r.netBuf.Count > 0 && Vector3.Distance(r.netBuf[r.netBuf.Count - 1].pos, s.pos) > 300f) r.netBuf.Clear();
                s.time = r.netClock;   // receive time on our clock
                r.netBuf.Add(s);
                if (r.netBuf.Count > 30) r.netBuf.RemoveAt(0);
                r.nextGate = s.nextGate;
                r.integrity = s.integrity;
            }
        }

        void OnPeerFinished(int id, float time, byte st)
        {
            if (race == null || !mpRace) return;
            foreach (var r in race.racers)
            {
                if (!r.pilot.remote || r.pilot.number != id) continue;
                r.state = (PilotState)st;
                if (r.state == PilotState.Finished) r.finishTime = time;
                else r.destroyTime = race.raceTime;
                foreach (var h in huds) h.Feed(UIKit.Colorize($"{r.pilot.name} {(r.state == PilotState.Finished ? "chegou em " + UIKit.Time(time) : "está fora")}", UIKit.Good));
            }
        }

        /// <summary>Called every frame during a network race: send our ship, place the others from their buffers.</summary>
        void UpdateNetRace(float dt)
        {
            if (!mpRace || net == null) return;
            net.Poll(dt);
            var me = humans.Count > 0 ? humans[0] : null;
            netSendT -= dt;
            if (me != null && netSendT <= 0f)
            {
                netSendT = 0.05f;
                net.SendState(new LanNet.ShipState
                {
                    pos = me.craft.position, yaw = me.craft.yaw, pitch = me.craft.visualPitch, roll = me.craft.roll, speed = me.craft.Speed,
                    nextGate = me.nextGate, state = (byte)me.state, integrity = me.integrity,
                });
                if (me.Done && !me.netFinishSent)
                {
                    me.netFinishSent = true;
                    net.SendFinished(me.finishTime, (byte)me.state);
                }
            }
            foreach (var r in race.racers)
            {
                if (!r.pilot.remote) continue;
                r.netClock += dt;
                var buf = r.netBuf;
                if (buf.Count == 0) continue;
                float t = r.netClock - NetDelay;
                var a = buf[0];
                var b = buf[buf.Count - 1];
                for (int i = 0; i + 1 < buf.Count; i++)
                    if (buf[i].time <= t && buf[i + 1].time >= t) { a = buf[i]; b = buf[i + 1]; break; }
                float k = b.time <= a.time ? 0f : Mathf.Clamp01((t - a.time) / (b.time - a.time));
                if (t > b.time) { a = b; k = 0f; }
                var c = r.craft;
                c.position = Vector3.Lerp(a.pos, b.pos, k);
                c.yaw = Mathf.LerpAngle(a.yaw * Mathf.Rad2Deg, b.yaw * Mathf.Rad2Deg, k) * Mathf.Deg2Rad;
                c.visualPitch = Mathf.Lerp(a.pitch, b.pitch, k);
                c.roll = Mathf.Lerp(a.roll, b.roll, k);
                c.vel = c.Forward * Mathf.Lerp(a.speed, b.speed, k);
                c.running = true;
                r.prevPos = c.position;
                r.prevYaw = c.yaw;
            }
        }
    }
}
