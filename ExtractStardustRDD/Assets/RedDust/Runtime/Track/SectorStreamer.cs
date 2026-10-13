using System.Collections.Generic;
using UnityEngine;

namespace RedDust.Track
{
    /// <summary>
    /// Streaming por distância para percursos longos (Doc 01 §20.3). Só fica ligada a geometria perto da câmera e dos
    /// pilotos (Focus): corredor, rochas, arcos e terreno fino. Os blocos de terreno grossos (24 m e 64 m) ficam sempre
    /// ligados e servem de LOD distante: debaixo do corredor o terreno já tem a forma do canyon (10-12 m abaixo).
    /// Os colliders vão com os objetos, por isso cada piloto tem de estar em Focus.
    /// </summary>
    public class SectorStreamer : MonoBehaviour
    {
        public float visibleRadius = 5000f;
        public float interval = 0.25f;

        /// <summary>Objetos à volta dos quais a geometria tem de existir (naves; a câmera principal entra sempre).</summary>
        public static readonly List<Transform> Focus = new List<Transform>();

        GameObject[] items;
        Bounds[] bounds;
        float timer;
        readonly List<Vector3> points = new List<Vector3>();

        public int ActiveCount { get; private set; }

        void Start()
        {
            var list = new List<GameObject>();
            var b = new List<Bounds>();
            foreach (var r in GetComponentsInChildren<MeshRenderer>(true))
            {
                string n = r.gameObject.name;
                if (n.StartsWith("GEO_Terrain") && (n.EndsWith("_64m") || n.EndsWith("_24m"))) continue;   // LOD distante
                list.Add(r.gameObject);
                b.Add(r.bounds);
            }
            items = list.ToArray();
            bounds = b.ToArray();
            timer = 0f;
        }

        void Update()
        {
            if (items == null) return;
            timer -= Time.unscaledDeltaTime;
            if (timer > 0f) return;
            timer = interval;
            points.Clear();
            if (Camera.main != null) points.Add(Camera.main.transform.position);
            for (int i = Focus.Count - 1; i >= 0; i--)
            {
                if (Focus[i] == null) { Focus.RemoveAt(i); continue; }
                points.Add(Focus[i].position);
            }
            if (points.Count == 0) return;
            float r2 = visibleRadius * visibleRadius;
            int active = 0;
            for (int i = 0; i < items.Length; i++)
            {
                float best = float.MaxValue;
                for (int k = 0; k < points.Count; k++) best = Mathf.Min(best, bounds[i].SqrDistance(points[k]));
                bool on = best < r2;
                if (items[i].activeSelf != on) items[i].SetActive(on);
                if (on) active++;
            }
            ActiveCount = active;
        }
    }
}
