using System;
using System.Collections.Generic;
using UnityEngine;

namespace Stardust
{
    /// <summary>Surface class of a model part; each class has its own material (texture layer, wind, ...).</summary>
    public enum MatClass { Rock, Bark, Concrete, Metal, Paint, Foliage, Plain, Glass }

    /// <summary>
    /// The Blender models of the island (WorldGen/blender/build_assets.py -> models.bytes), imported as meshes
    /// with one submesh per material class. Built by the editor importer (Stardust/Import World).
    /// </summary>
    public class ModelLibrary : ScriptableObject
    {
        [Serializable]
        public class Entry
        {
            public string name;
            public Mesh mesh;
            public MatClass[] classes;   // material class of each submesh
            public Bounds bounds;
        }

        public List<Entry> models = new List<Entry>();
        public Material[] materials;      // indexed by MatClass
        public Material[] shipMaterials;  // same classes, object-space projection (for vehicles)

        Dictionary<string, Entry> map;

        public Entry Get(string name)
        {
            if (map == null)
            {
                map = new Dictionary<string, Entry>();
                foreach (var e in models) map[e.name] = e;
            }
            if (name.EndsWith("_big")) name = name.Substring(0, name.Length - 4);
            map.TryGetValue(name, out var r);
            return r;
        }

        public Material[] MaterialsFor(Entry e, bool ship = false)
        {
            var src = ship && shipMaterials != null && shipMaterials.Length > 0 ? shipMaterials : materials;
            var m = new Material[e.classes.Length];
            for (int i = 0; i < m.Length; i++) m[i] = src[(int)e.classes[i]];
            return m;
        }

        static ModelLibrary instance;
        public static ModelLibrary I
        {
            get
            {
                if (instance == null) instance = Resources.Load<ModelLibrary>(IslandData.Root + "Models");
                return instance;
            }
        }
    }
}
