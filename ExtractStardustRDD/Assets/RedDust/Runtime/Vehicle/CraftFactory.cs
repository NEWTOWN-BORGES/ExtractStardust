using UnityEngine;

namespace RedDust.Vehicle
{
    /// <summary>
    /// Cria o corpo físico de uma nave a partir dos dados (envelope, massa, centro de massa). O visual é montado
    /// à parte e nunca altera collider nem centro de massa (Doc 02 §12).
    /// </summary>
    public static class CraftFactory
    {
        static PhysicsMaterial hullMaterial;

        public static CraftController CreateCore(string name, CraftTuning tuning, bool interpolate = true)
        {
            var go = new GameObject(name) { layer = Layers.Craft };
            var rb = go.AddComponent<Rigidbody>();
            rb.interpolation = interpolate ? RigidbodyInterpolation.Interpolate : RigidbodyInterpolation.None;
            var box = go.AddComponent<BoxCollider>();
            box.size = tuning.hullSize;
            box.center = Vector3.zero;
            hullMaterial ??= new PhysicsMaterial("CraftHull")
            {
                dynamicFriction = 0.12f,
                staticFriction = 0.12f,
                bounciness = 0.05f,
                frictionCombine = PhysicsMaterialCombine.Minimum,
                bounceCombine = PhysicsMaterialCombine.Minimum,
            };
            box.sharedMaterial = hullMaterial;
            var craft = go.AddComponent<CraftController>();
            craft.tuning = tuning;
            craft.Init();
            return craft;
        }
    }
}
