using UnityEngine;

namespace Stardust
{
    /// <summary>Keeps a full-screen UI rect inside Screen.safeArea (phone notches and rounded corners).</summary>
    [RequireComponent(typeof(RectTransform))]
    public class SafeArea : MonoBehaviour
    {
        Rect last;
        Vector2Int lastSize;

        void LateUpdate()
        {
            var sa = Screen.safeArea;
            var size = new Vector2Int(Screen.width, Screen.height);
            if (sa == last && size == lastSize) return;
            last = sa;
            lastSize = size;
            if (size.x <= 0 || size.y <= 0) return;
            var rt = (RectTransform)transform;
            rt.anchorMin = new Vector2(sa.xMin / size.x, sa.yMin / size.y);
            rt.anchorMax = new Vector2(sa.xMax / size.x, sa.yMax / size.y);
            rt.offsetMin = rt.offsetMax = Vector2.zero;
        }
    }
}
