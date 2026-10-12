using System;
using System.Collections.Generic;
using System.Net;
using System.Net.NetworkInformation;
using System.Net.Sockets;
using System.Text;
using UnityEngine;

namespace Stardust
{
    /// <summary>
    /// Wi-Fi multiplayer (port of RACESTARS net.gd) over plain UDP: one device CREATES the game and the others JOIN
    /// on the same network (or the hotspot of one of them). Discovery: the searcher broadcasts "XSTAR?" (and also
    /// sends it to every address of its /24, some phones block broadcast); the host answers with its name.
    /// Star topology: clients talk to the host, the host relays. Up to 4 players, ship states ~20 times a second.
    /// Important messages (start, go, finish) are repeated a few times; duplicates are ignored.
    /// </summary>
    public class LanNet
    {
        public const int GamePort = 47777, DiscPort = 47778, MaxPlayers = 4;
        public static readonly Color[] Colors = { new Color(1f, 0.48f, 0.18f), new Color(0.25f, 0.66f, 1f), new Color(0.37f, 0.88f, 0.42f), new Color(0.77f, 0.42f, 1f) };

        enum Msg : byte { Join = 1, Welcome = 2, Players = 3, Start = 4, Ready = 5, Go = 6, State = 7, Finish = 8, Leave = 9, Ping = 10 }

        public class Player
        {
            public int id;
            public string name;
            public int color;
            public IPEndPoint ep;      // host side
            public float seen;
            public bool ready;
        }

        public class HostInfo { public string ip, name; public int count; public float seen; }

        public struct ShipState
        {
            public int id;
            public Vector3 pos;
            public float yaw, pitch, roll, speed;
            public int nextGate;
            public byte state;
            public float integrity;
            public float time;   // sender clock
        }

        public bool online, isHost;
        public int myId = 1;
        public string myName = "Jogador";
        public string status = "";
        public readonly Dictionary<int, Player> players = new Dictionary<int, Player>();
        public readonly Dictionary<string, HostInfo> hosts = new Dictionary<string, HostInfo>();
        public event Action PlayersChanged, CountdownGo, BackToMenu;
        public event Action<string, int> StartRace;          // event id, seed
        public event Action<ShipState> PeerState;
        public event Action<int, float, byte> PeerFinished;  // id, time, final state

        UdpClient game, disc, probe;
        IPEndPoint hostEp;
        float clock, probeT, pingT, lastHostSeen;
        string lastStartKey = "";
        bool sawGo;
        readonly HashSet<string> seenFinish = new HashSet<string>();
        readonly List<(byte[] data, IPEndPoint to, int left, float t)> repeats = new List<(byte[], IPEndPoint, int, float)>();

        public Color ColorOf(int id) => players.TryGetValue(id, out var p) ? Colors[p.color % Colors.Length] : Color.white;
        public List<int> SortedIds() { var l = new List<int>(players.Keys); l.Sort(); return l; }

        // ------------------------------------------------------------------ create / join / leave

        public bool Host()
        {
            Leave();
            try
            {
                game = new UdpClient(GamePort);
                try { disc = new UdpClient(DiscPort); } catch { disc = null; }
            }
            catch (Exception e)
            {
                status = "Não foi possível criar o jogo (porta ocupada?).";
                Debug.LogWarning("[net] host: " + e.Message);
                Leave();
                return false;
            }
            online = true;
            isHost = true;
            myId = 1;
            players.Clear();
            players[1] = new Player { id = 1, name = myName, color = 0, seen = clock };
            status = "Jogo criado. À espera de jogadores…";
            PlayersChanged?.Invoke();
            return true;
        }

        public bool Join(string ip)
        {
            LeaveKeepProbe();
            try
            {
                hostEp = new IPEndPoint(IPAddress.Parse(ip), GamePort);
                game = new UdpClient(0);
            }
            catch (Exception e)
            {
                status = "Endereço inválido.";
                Debug.LogWarning("[net] join: " + e.Message);
                return false;
            }
            online = true;
            isHost = false;
            myId = 0;
            lastHostSeen = clock;
            status = $"A ligar a {ip}…";
            Send(Pack(Msg.Join, w => w.Str(myName)), hostEp, 3);
            return true;
        }

        public void LeaveKeepProbe()
        {
            if (online && game != null)
            {
                var bye = Pack(Msg.Leave, w => w.I8(myId));
                try
                {
                    if (isHost) foreach (var p in players.Values) { if (p.ep != null) game.Send(bye, bye.Length, p.ep); }
                    else if (hostEp != null) game.Send(bye, bye.Length, hostEp);
                }
                catch { }
            }
            game?.Close(); game = null;
            disc?.Close(); disc = null;
            online = false;
            isHost = false;
            players.Clear();
            repeats.Clear();
            lastStartKey = "";
            sawGo = false;
            seenFinish.Clear();
        }

        public void Leave()
        {
            LeaveKeepProbe();
            StopSearch();
        }

        public void StartSearch()
        {
            StopSearch();
            hosts.Clear();
            try
            {
                probe = new UdpClient(0) { EnableBroadcast = true };
            }
            catch (Exception e) { Debug.LogWarning("[net] probe: " + e.Message); probe = null; }
            probeT = 0f;
        }

        public void StopSearch()
        {
            probe?.Close();
            probe = null;
        }

        public static List<string> LocalIPs()
        {
            var outIps = new List<string>();
            try
            {
                foreach (var ni in NetworkInterface.GetAllNetworkInterfaces())
                {
                    if (ni.OperationalStatus != OperationalStatus.Up) continue;
                    foreach (var ua in ni.GetIPProperties().UnicastAddresses)
                    {
                        if (ua.Address.AddressFamily != AddressFamily.InterNetwork) continue;
                        var s = ua.Address.ToString();
                        if (s.StartsWith("127.") || s.StartsWith("169.254.")) continue;
                        outIps.Add(s);
                    }
                }
            }
            catch { }
            if (outIps.Count == 0)
            {
                try { foreach (var a in Dns.GetHostAddresses(Dns.GetHostName())) if (a.AddressFamily == AddressFamily.InterNetwork && !a.ToString().StartsWith("127.")) outIps.Add(a.ToString()); }
                catch { }
            }
            return outIps;
        }

        // ------------------------------------------------------------------ messages

        class W
        {
            readonly List<byte> b = new List<byte>(64);
            public W I8(int v) { b.Add((byte)v); return this; }
            public W I32(int v) { b.AddRange(BitConverter.GetBytes(v)); return this; }
            public W F(float v) { b.AddRange(BitConverter.GetBytes(v)); return this; }
            public W Str(string s) { var d = Encoding.UTF8.GetBytes(s ?? ""); b.Add((byte)Mathf.Min(d.Length, 255)); for (int i = 0; i < Mathf.Min(d.Length, 255); i++) b.Add(d[i]); return this; }
            public byte[] Bytes => b.ToArray();
        }

        class R
        {
            readonly byte[] d; int o;
            public R(byte[] data, int offset) { d = data; o = offset; }
            public int I8() => d[o++];
            public int I32() { int v = BitConverter.ToInt32(d, o); o += 4; return v; }
            public float F() { float v = BitConverter.ToSingle(d, o); o += 4; return v; }
            public string Str() { int n = d[o++]; var s = Encoding.UTF8.GetString(d, o, n); o += n; return s; }
        }

        static byte[] Pack(Msg m, Action<W> body)
        {
            var w = new W();
            w.I8((int)m);
            body?.Invoke(w);
            return w.Bytes;
        }

        void Send(byte[] data, IPEndPoint to, int times = 1)
        {
            if (game == null || to == null) return;
            try { game.Send(data, data.Length, to); } catch (Exception e) { Debug.LogWarning("[net] send: " + e.Message); }
            if (times > 1) repeats.Add((data, to, times - 1, clock + 0.15f));
        }

        void ToAll(byte[] data, int times = 1, int except = -1)
        {
            if (isHost)
            {
                foreach (var p in players.Values) if (p.ep != null && p.id != except) Send(data, p.ep, times);
            }
            else Send(data, hostEp, times);
        }

        void SyncPlayers()
        {
            var msg = Pack(Msg.Players, w =>
            {
                w.I8(players.Count);
                foreach (var p in players.Values) { w.I8(p.id); w.I8(p.color); w.Str(p.name); }
            });
            ToAll(msg, 2);
            PlayersChanged?.Invoke();
        }

        /// <summary>Host: everyone goes to the race with the same event and seed.</summary>
        public void HostStart(string eventId, int seed)
        {
            if (!isHost) return;
            foreach (var p in players.Values) p.ready = p.id == 1;
            sawGo = false;
            var msg = Pack(Msg.Start, w => { w.Str(eventId); w.I32(seed); });
            ToAll(msg, 4);
            lastStartKey = eventId + seed;
            StartRace?.Invoke(eventId, seed);
        }

        /// <summary>The race of this device finished loading.</summary>
        public void ReportReady()
        {
            if (!online) return;
            if (isHost) { players[1].ready = true; CheckAllReady(); }
            else Send(Pack(Msg.Ready, w => w.I8(myId)), hostEp, 3);
        }

        void CheckAllReady()
        {
            foreach (var p in players.Values) if (!p.ready) return;
            if (sawGo) return;
            sawGo = true;
            ToAll(Pack(Msg.Go, null), 4);
            CountdownGo?.Invoke();
        }

        public void SendState(ShipState s)
        {
            if (!online || game == null) return;
            var msg = Pack(Msg.State, w =>
            {
                w.I8(myId); w.F(s.pos.x); w.F(s.pos.y); w.F(s.pos.z); w.F(s.yaw); w.F(s.pitch); w.F(s.roll); w.F(s.speed);
                w.I8(Mathf.Clamp(s.nextGate, 0, 255)); w.I8(s.state); w.F(s.integrity); w.F(clock);
            });
            ToAll(msg);
        }

        public void SendFinished(float time, byte finalState)
        {
            if (!online) return;
            var msg = Pack(Msg.Finish, w => { w.I8(myId); w.F(time); w.I8(finalState); });
            ToAll(msg, 4);
        }

        // ------------------------------------------------------------------ per frame

        public void Poll(float dt)
        {
            clock += dt;
            for (int i = repeats.Count - 1; i >= 0; i--)
            {
                var r = repeats[i];
                if (clock < r.t) continue;
                try { game?.Send(r.data, r.data.Length, r.to); } catch { }
                if (r.left <= 1) repeats.RemoveAt(i);
                else repeats[i] = (r.data, r.to, r.left - 1, clock + 0.15f);
            }
            // discovery: the host answers searches
            if (disc != null)
            {
                try
                {
                    while (disc.Available > 0)
                    {
                        IPEndPoint from = null;
                        var d = disc.Receive(ref from);
                        if (Encoding.UTF8.GetString(d) == "XSTAR?")
                        {
                            var reply = Encoding.UTF8.GetBytes($"XSTAR!{myName}|{players.Count}");
                            disc.Send(reply, reply.Length, from);
                        }
                    }
                }
                catch (Exception e) { Debug.LogWarning("[net] disc: " + e.Message); }
            }
            if (probe != null) PollProbe(dt);
            if (game == null) return;
            try
            {
                while (game.Available > 0)
                {
                    IPEndPoint from = null;
                    var d = game.Receive(ref from);
                    if (d.Length > 0) Handle(d, from);
                }
            }
            catch (Exception e) { Debug.LogWarning("[net] recv: " + e.Message); }
            // keep-alive and time-outs
            pingT -= dt;
            if (pingT <= 0f)
            {
                pingT = 1f;
                ToAll(Pack(Msg.Ping, w => w.I8(myId)));
                if (isHost)
                {
                    var gone = new List<int>();
                    foreach (var p in players.Values) if (p.id != 1 && clock - p.seen > 6f) gone.Add(p.id);
                    foreach (var id in gone) players.Remove(id);
                    if (gone.Count > 0) SyncPlayers();
                }
                else if (online && clock - lastHostSeen > 8f)
                {
                    status = "O anfitrião saiu.";
                    Leave();
                    BackToMenu?.Invoke();
                }
            }
        }

        void PollProbe(float dt)
        {
            probeT -= dt;
            if (probeT <= 0f)
            {
                probeT = 1.5f;
                var msg = Encoding.UTF8.GetBytes("XSTAR?");
                try { probe.Send(msg, msg.Length, new IPEndPoint(IPAddress.Broadcast, DiscPort)); } catch { }
                foreach (var ip in LocalIPs())
                {
                    var b = ip.Substring(0, ip.LastIndexOf('.') + 1);
                    for (int k = 1; k < 255; k++)
                    {
                        try { probe.Send(msg, msg.Length, new IPEndPoint(IPAddress.Parse(b + k), DiscPort)); } catch { }
                    }
                }
            }
            bool changed = false;
            try
            {
                while (probe.Available > 0)
                {
                    IPEndPoint from = null;
                    var d = probe.Receive(ref from);
                    var s = Encoding.UTF8.GetString(d);
                    if (!s.StartsWith("XSTAR!")) continue;
                    var parts = s.Substring(6).Split('|');
                    var ip = from.Address.ToString();
                    hosts[ip] = new HostInfo { ip = ip, name = parts[0], count = parts.Length > 1 && int.TryParse(parts[1], out int c) ? c : 1, seen = clock };
                    changed = true;
                }
            }
            catch { }
            var old = new List<string>();
            foreach (var h in hosts.Values) if (clock - h.seen > 6f) old.Add(h.ip);
            foreach (var ip in old) { hosts.Remove(ip); changed = true; }
            if (changed) PlayersChanged?.Invoke();
        }

        void Handle(byte[] d, IPEndPoint from)
        {
            var r = new R(d, 1);
            var m = (Msg)d[0];
            if (!isHost) lastHostSeen = clock;
            switch (m)
            {
                case Msg.Join when isHost:
                {
                    string name = r.Str();
                    Player p = null;
                    foreach (var q in players.Values) if (q.ep != null && q.ep.Equals(from)) p = q;
                    if (p == null)
                    {
                        if (players.Count >= MaxPlayers) return;
                        int id = 2;
                        while (players.ContainsKey(id)) id++;
                        var used = new HashSet<int>();
                        foreach (var q in players.Values) used.Add(q.color);
                        int c = 0;
                        while (used.Contains(c)) c++;
                        p = new Player { id = id, name = string.IsNullOrEmpty(name) ? $"Jogador {id}" : name, color = c, ep = from };
                        players[id] = p;
                    }
                    p.seen = clock;
                    Send(Pack(Msg.Welcome, w => w.I8(p.id)), from, 2);
                    SyncPlayers();
                    break;
                }
                case Msg.Welcome when !isHost:
                    myId = r.I8();
                    status = "Ligado! À espera que o anfitrião comece.";
                    StopSearch();
                    PlayersChanged?.Invoke();
                    break;
                case Msg.Players when !isHost:
                {
                    players.Clear();
                    int n = r.I8();
                    for (int i = 0; i < n; i++)
                    {
                        int id = r.I8(), c = r.I8();
                        players[id] = new Player { id = id, color = c, name = r.Str() };
                    }
                    PlayersChanged?.Invoke();
                    break;
                }
                case Msg.Start when !isHost:
                {
                    string ev = r.Str();
                    int seed = r.I32();
                    if (lastStartKey == ev + seed) return;
                    lastStartKey = ev + seed;
                    sawGo = false;
                    StartRace?.Invoke(ev, seed);
                    break;
                }
                case Msg.Ready when isHost:
                {
                    int id = r.I8();
                    if (players.TryGetValue(id, out var p)) { p.ready = true; p.seen = clock; }
                    CheckAllReady();
                    break;
                }
                case Msg.Go when !isHost:
                    if (sawGo) return;
                    sawGo = true;
                    CountdownGo?.Invoke();
                    break;
                case Msg.State:
                {
                    var s = new ShipState
                    {
                        id = r.I8(), pos = new Vector3(r.F(), r.F(), r.F()), yaw = r.F(), pitch = r.F(), roll = r.F(), speed = r.F(),
                        nextGate = r.I8(), state = (byte)r.I8(), integrity = r.F(), time = r.F(),
                    };
                    if (isHost)
                    {
                        if (players.TryGetValue(s.id, out var p)) p.seen = clock;
                        ToAll(d, 1, s.id);   // relay to the other clients
                    }
                    if (s.id != myId) PeerState?.Invoke(s);
                    break;
                }
                case Msg.Finish:
                {
                    int id = r.I8();
                    float t = r.F();
                    byte st = (byte)r.I8();
                    string key = id + ":" + t.ToString("0.000");
                    if (!seenFinish.Add(key)) return;
                    if (isHost) ToAll(d, 3, id);
                    if (id != myId) PeerFinished?.Invoke(id, t, st);
                    break;
                }
                case Msg.Leave:
                {
                    int id = r.I8();
                    if (isHost) { if (players.Remove(id)) SyncPlayers(); }
                    else if (id == 1) { status = "O anfitrião saiu."; Leave(); BackToMenu?.Invoke(); }
                    break;
                }
                case Msg.Ping:
                {
                    int id = r.I8();
                    if (isHost && players.TryGetValue(id, out var p)) p.seen = clock;
                    break;
                }
            }
        }
    }
}
