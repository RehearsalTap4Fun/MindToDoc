// 从 Unity 工程导出现有界面的图层，供交互预演网页使用。只读：在预览场景里实例化 prefab，不改动工程资源与当前场景。
// 用法：把 __SPEC_PATH__ 换成规格文件的绝对路径，整段作为方法体交给 Unity 编辑器执行（UnityMCP execute_code）。
// 规格与输出格式见 references/interactive-preview-reference.md「还原现有界面」。
var specPath = "__SPEC_PATH__";
var spec = Newtonsoft.Json.Linq.JObject.Parse(System.IO.File.ReadAllText(specPath));
var outDir = (string)spec["out"];
if (!System.IO.Path.IsPathRooted(outDir)) outDir = System.IO.Path.Combine(System.IO.Path.GetDirectoryName(specPath), outDir); // 相对路径以规格文件所在目录为准
System.IO.Directory.CreateDirectory(outDir);
float W = spec["design"] != null ? (float)spec["design"][0] : 1080f;
float H = spec["design"] != null ? (float)spec["design"][1] : 1920f;
float scale = spec["scale"] != null ? (float)spec["scale"] : 0.5f;
int pw = UnityEngine.Mathf.RoundToInt(W * scale), ph = UnityEngine.Mathf.RoundToInt(H * scale);
var log = new System.Text.StringBuilder();

System.Func<UnityEngine.Transform, UnityEngine.Transform, string> pathOf = (node, top) => {
  var p = ""; var t = node;
  while (t != null && t != top) { p = p.Length == 0 ? t.name : t.name + "/" + p; t = t.parent; }
  return p;
};
System.Func<UnityEngine.RectTransform, Newtonsoft.Json.Linq.JObject> rectOf = (r) => {
  var c = new UnityEngine.Vector3[4]; r.GetWorldCorners(c);
  var o = new Newtonsoft.Json.Linq.JObject();
  o["x"] = UnityEngine.Mathf.RoundToInt(c[0].x + W / 2f); o["y"] = UnityEngine.Mathf.RoundToInt(H / 2f - c[1].y);
  o["w"] = UnityEngine.Mathf.RoundToInt(c[2].x - c[0].x); o["h"] = UnityEngine.Mathf.RoundToInt(c[1].y - c[0].y);
  return o;
};
System.Func<UnityEngine.Camera, UnityEngine.Color, UnityEngine.Color[]> shoot = (cam, bg) => {
  var rt = new UnityEngine.RenderTexture(pw, ph, 24);
  cam.backgroundColor = bg; cam.targetTexture = rt; cam.Render();
  var prev = UnityEngine.RenderTexture.active; UnityEngine.RenderTexture.active = rt;
  var tex = new UnityEngine.Texture2D(pw, ph, UnityEngine.TextureFormat.RGBA32, false);
  tex.ReadPixels(new UnityEngine.Rect(0, 0, pw, ph), 0, 0); tex.Apply();
  UnityEngine.RenderTexture.active = prev; cam.targetTexture = null; rt.Release();
  var px = tex.GetPixels(); UnityEngine.Object.DestroyImmediate(tex);
  return px;
};

foreach (Newtonsoft.Json.Linq.JObject layer in (Newtonsoft.Json.Linq.JArray)spec["layers"]) {
  var name = (string)layer["name"];
  var prefab = UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.GameObject>((string)layer["prefab"]);
  if (prefab == null) { log.AppendLine(name + ": 找不到 prefab " + layer["prefab"]); continue; }
  var scene = UnityEditor.SceneManagement.EditorSceneManager.NewPreviewScene();
  try {
    var camGo = new UnityEngine.GameObject("pvcam");
    UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(camGo, scene);
    var cam = camGo.AddComponent<UnityEngine.Camera>();
    cam.scene = scene; cam.orthographic = true; cam.orthographicSize = H / 2f; cam.aspect = W / H;
    cam.clearFlags = UnityEngine.CameraClearFlags.SolidColor; cam.cullingMask = -1;
    cam.transform.position = new UnityEngine.Vector3(0, 0, -500); cam.nearClipPlane = 1f; cam.farClipPlane = 2000f;

    var inst = (UnityEngine.GameObject)UnityEditor.PrefabUtility.InstantiatePrefab(prefab, scene);
    var canvas = inst.GetComponent<UnityEngine.Canvas>();
    UnityEngine.RectTransform stage;
    if (canvas != null) {
      stage = (UnityEngine.RectTransform)inst.transform;
    } else {
      // 列表条目等不带 Canvas 的子 prefab：包一层画布，保持自身尺寸。
      var wrap = new UnityEngine.GameObject("pvcanvas", typeof(UnityEngine.Canvas));
      UnityEngine.SceneManagement.SceneManager.MoveGameObjectToScene(wrap, scene);
      canvas = wrap.GetComponent<UnityEngine.Canvas>(); stage = (UnityEngine.RectTransform)wrap.transform;
      inst.transform.SetParent(stage, false);
    }
    var scaler = stage.GetComponent<UnityEngine.UI.CanvasScaler>(); if (scaler != null) scaler.enabled = false;
    canvas.renderMode = UnityEngine.RenderMode.WorldSpace; canvas.worldCamera = cam;
    stage.localScale = UnityEngine.Vector3.one; stage.sizeDelta = new UnityEngine.Vector2(W, H); stage.position = UnityEngine.Vector3.zero;
    var top = inst.transform;
    System.Func<string, UnityEngine.Transform> find = (p) => {
      if (string.IsNullOrEmpty(p)) return top;
      var t = top.Find(p);
      if (t == null) log.AppendLine(name + ": 找不到节点 " + p);
      return t;
    };

    // solo：只渲染某个子树，沿父链关掉其余兄弟节点。
    var rootNode = find((string)layer["root"]);
    if (rootNode == null) rootNode = top;
    for (var t = rootNode; t != top && t != null; t = t.parent) {
      t.gameObject.SetActive(true);
      foreach (UnityEngine.Transform sib in t.parent) if (sib != t) sib.gameObject.SetActive(false);
    }
    foreach (var p in layer["show"] ?? new Newtonsoft.Json.Linq.JArray()) { var t = find((string)p); if (t != null) t.gameObject.SetActive(true); }
    foreach (var p in layer["hide"] ?? new Newtonsoft.Json.Linq.JArray()) { var t = find((string)p); if (t != null) t.gameObject.SetActive(false); }
    // 绑定了多语言 key 的文本会用 key 的文案覆盖写入值：先清掉实例上的 key，再写文字。
    System.Action<UnityEngine.UI.Text, string> setText = (txt, v) => {
      var so = new UnityEditor.SerializedObject(txt);
      var key = so.FindProperty("m_Key");
      if (key != null && key.propertyType == UnityEditor.SerializedPropertyType.String && key.stringValue.Length > 0) {
        key.stringValue = ""; so.ApplyModifiedPropertiesWithoutUndo();
      }
      txt.text = v;
      if (txt.text == v) return;
      so.Update(); so.FindProperty("m_Text").stringValue = v; so.ApplyModifiedPropertiesWithoutUndo();
      txt.SetAllDirty();
      if (txt.text != v) log.AppendLine(name + ": 文字写入未生效，改用文字槽覆盖 " + txt.name);
    };
    System.Action<bool> applyText = (report) => {
      if (layer["text"] == null) return;
      foreach (var kv in (Newtonsoft.Json.Linq.JObject)layer["text"]) {
        var t = top.Find(kv.Key); var txt = t != null ? t.GetComponent<UnityEngine.UI.Text>() : null;
        if (txt != null) setText(txt, (string)kv.Value); else if (report) log.AppendLine(name + ": 找不到文本节点 " + kv.Key);
      }
    };
    System.Action relayout = () => {
      UnityEngine.Canvas.ForceUpdateCanvases();
      UnityEngine.UI.LayoutRebuilder.ForceRebuildLayoutImmediate(stage);
      UnityEngine.Canvas.ForceUpdateCanvases();
    };
    applyText(true); relayout();
    applyText(false); relayout(); // 部分组件在激活时会重置文字，排版后再写一次
    // 个别组件会把被隐藏的节点重新激活：仍然可见时，直接停掉它下面的全部图形。
    foreach (var p in layer["hide"] ?? new Newtonsoft.Json.Linq.JArray()) {
      var t = top.Find((string)p);
      if (t == null || !t.gameObject.activeInHierarchy) continue;
      foreach (var g in t.GetComponentsInChildren<UnityEngine.UI.Graphic>(true)) g.enabled = false;
    }
    // invisible：不画出来但保留排版占位（例如奖励格、列表条目的模板），网页在该区域另行摆放内容。
    foreach (var p in layer["invisible"] ?? new Newtonsoft.Json.Linq.JArray()) {
      var t = find((string)p); if (t == null) continue;
      foreach (var g in t.GetComponentsInChildren<UnityEngine.UI.Graphic>(true)) g.enabled = false;
    }
    // place：把子树移到设计分辨率下的指定左上角位置（用于从屏幕外滑入的面板）。
    if (layer["place"] != null) {
      var r0 = rectOf((UnityEngine.RectTransform)rootNode);
      rootNode.position += new UnityEngine.Vector3((float)layer["place"][0] - (int)r0["x"], -((float)layer["place"][1] - (int)r0["y"]), 0f);
      UnityEngine.Canvas.ForceUpdateCanvases();
    }

    var meta = new Newtonsoft.Json.Linq.JObject();
    var slots = new Newtonsoft.Json.Linq.JObject();
    // slots：运行时才确定的文字。按占位文字量出位置后把它变透明（保留排版占位），由网页按同一位置、字号、颜色覆盖显示。
    // 写法：{槽名: 节点路径}，或 {槽名: {node, blank: [同一按钮上其余要清空的文字节点], outline: "#描边色"}}。
    if (layer["slots"] != null) {
      foreach (var kv in (Newtonsoft.Json.Linq.JObject)layer["slots"]) {
        var cfg = kv.Value as Newtonsoft.Json.Linq.JObject;
        var t = find(cfg != null ? (string)cfg["node"] : (string)kv.Value); var txt = t != null ? t.GetComponent<UnityEngine.UI.Text>() : null;
        if (txt == null) { log.AppendLine(name + ": 文字槽没有文本组件 " + kv.Value); continue; }
        var s = rectOf((UnityEngine.RectTransform)t);
        s["pivot"] = ((UnityEngine.RectTransform)t).pivot.x;
        s["fontSize"] = txt.fontSize; s["color"] = "#" + UnityEngine.ColorUtility.ToHtmlStringRGB(txt.color);
        s["align"] = txt.alignment.ToString(); s["bold"] = txt.fontStyle == UnityEngine.FontStyle.Bold || txt.fontStyle == UnityEngine.FontStyle.BoldAndItalic;
        s["sample"] = txt.text;
        // 定宽且自动换行的正文：网页在同一矩形内换行排版。
        var fit = t.GetComponent<UnityEngine.UI.ContentSizeFitter>();
        if (txt.horizontalOverflow == UnityEngine.HorizontalWrapMode.Wrap && (fit == null || fit.horizontalFit == UnityEngine.UI.ContentSizeFitter.FitMode.Unconstrained)) s["wrap"] = true;
        var ol = t.GetComponent<UnityEngine.UI.Shadow>();
        if (ol != null) s["outline"] = "#" + UnityEngine.ColorUtility.ToHtmlStringRGB(ol.effectColor);
        if (cfg != null && cfg["outline"] != null) s["outline"] = (string)cfg["outline"];
        slots[kv.Key] = s;
        var clear = txt.color; clear.a = 0f; txt.color = clear;
        foreach (var fx in t.GetComponents<UnityEngine.UI.BaseMeshEffect>()) fx.enabled = false;
        if (cfg != null && cfg["blank"] != null) foreach (var b in cfg["blank"]) {
          var bt = find((string)b); var btxt = bt != null ? bt.GetComponent<UnityEngine.UI.Text>() : null;
          if (btxt != null) { var bc = btxt.color; bc.a = 0f; btxt.color = bc; foreach (var fx in bt.GetComponents<UnityEngine.UI.BaseMeshEffect>()) fx.enabled = false; }
        }
      }
      UnityEngine.Canvas.ForceUpdateCanvases();
    }
    var hotspots = new Newtonsoft.Json.Linq.JObject();
    if (layer["hotspots"] != null) foreach (var kv in (Newtonsoft.Json.Linq.JObject)layer["hotspots"]) {
      var t = find((string)kv.Value); if (t != null) hotspots[kv.Key] = rectOf((UnityEngine.RectTransform)t);
    }

    // 图层范围：整屏，或子树根节点的矩形。
    bool full = rootNode == top || (layer["full"] != null && (bool)layer["full"]);
    int bx = 0, by = 0, bw = UnityEngine.Mathf.RoundToInt(W), bh = UnityEngine.Mathf.RoundToInt(H);
    if (!full) {
      var r = rectOf((UnityEngine.RectTransform)rootNode);
      int pad = layer["pad"] != null ? (int)layer["pad"] : 0;
      bx = UnityEngine.Mathf.Clamp((int)r["x"] - pad, 0, bw); by = UnityEngine.Mathf.Clamp((int)r["y"] - pad, 0, bh);
      bw = UnityEngine.Mathf.Clamp((int)r["w"] + pad * 2, 1, UnityEngine.Mathf.RoundToInt(W) - bx);
      bh = UnityEngine.Mathf.Clamp((int)r["h"] + pad * 2, 1, UnityEngine.Mathf.RoundToInt(H) - by);
    }

    // 黑底、白底各渲染一次，还原每个像素的真实透明度与颜色。
    bool transparent = layer["transparent"] == null || (bool)layer["transparent"];
    var onBlack = shoot(cam, UnityEngine.Color.black);
    var px = onBlack;
    if (transparent) {
      var onWhite = shoot(cam, UnityEngine.Color.white);
      px = new UnityEngine.Color[onBlack.Length];
      for (int i = 0; i < px.Length; i++) {
        var b = onBlack[i]; var w = onWhite[i];
        float a = 1f - UnityEngine.Mathf.Clamp01(((w.r - b.r) + (w.g - b.g) + (w.b - b.b)) / 3f);
        px[i] = a <= 0.004f ? new UnityEngine.Color(0, 0, 0, 0) : new UnityEngine.Color(b.r / a, b.g / a, b.b / a, a);
      }
    } else {
      for (int i = 0; i < px.Length; i++) px[i].a = 1f;
    }
    int cx = UnityEngine.Mathf.RoundToInt(bx * scale), cw = UnityEngine.Mathf.Max(1, UnityEngine.Mathf.RoundToInt(bw * scale));
    int chh = UnityEngine.Mathf.Max(1, UnityEngine.Mathf.RoundToInt(bh * scale)), cyTop = UnityEngine.Mathf.RoundToInt(by * scale);
    cw = UnityEngine.Mathf.Min(cw, pw - cx); chh = UnityEngine.Mathf.Min(chh, ph - cyTop);
    var crop = new UnityEngine.Texture2D(cw, chh, UnityEngine.TextureFormat.RGBA32, false);
    var cpx = new UnityEngine.Color[cw * chh];
    int srcY0 = ph - cyTop - chh; // 纹理原点在左下
    for (int y = 0; y < chh; y++) System.Array.Copy(px, (srcY0 + y) * pw + cx, cpx, y * cw, cw);
    crop.SetPixels(cpx); crop.Apply();
    System.IO.File.WriteAllBytes(outDir + "/" + name + ".png", UnityEngine.ImageConversion.EncodeToPNG(crop));
    UnityEngine.Object.DestroyImmediate(crop);

    meta["name"] = name; meta["prefab"] = (string)layer["prefab"]; meta["image"] = name + ".png";
    if (layer["title"] != null) meta["title"] = (string)layer["title"]; // 给人看的界面名与使用说明，原样带到图层信息里
    if (layer["note"] != null) meta["note"] = (string)layer["note"];
    meta["x"] = bx; meta["y"] = by; meta["w"] = bw; meta["h"] = bh;
    meta["hotspots"] = hotspots; meta["slots"] = slots;

    // survey：列出全部节点，用来找路径、文字与按钮。
    if (layer["survey"] != null && (bool)layer["survey"]) {
      var nodes = new Newtonsoft.Json.Linq.JArray();
      foreach (var rt in inst.GetComponentsInChildren<UnityEngine.RectTransform>(true)) {
        if (rt.transform == top) continue;
        var n = rectOf(rt);
        n["path"] = pathOf(rt.transform, top); n["active"] = rt.gameObject.activeInHierarchy;
        var txt = rt.GetComponent<UnityEngine.UI.Text>();
        if (txt != null) { n["text"] = txt.text; n["fontSize"] = txt.fontSize; n["color"] = "#" + UnityEngine.ColorUtility.ToHtmlStringRGB(txt.color); }
        var img = rt.GetComponent<UnityEngine.UI.Image>();
        if (img != null && img.sprite != null) n["sprite"] = img.sprite.name;
        if (rt.GetComponent<UnityEngine.UI.Selectable>() != null) n["button"] = true;
        var others = new System.Collections.Generic.List<string>();
        foreach (var comp in rt.GetComponents<UnityEngine.MonoBehaviour>()) {
          if (comp == null) continue; var tn = comp.GetType().Name;
          if (!tn.StartsWith("TFW") && tn != "Text" && tn != "Image" && tn != "Outline" && tn != "Shadow") others.Add(tn);
        }
        if (others.Count > 0) n["comps"] = string.Join(",", others);
        nodes.Add(n);
      }
      meta["nodes"] = nodes;
    }
    System.IO.File.WriteAllText(outDir + "/" + name + ".json", meta.ToString(Newtonsoft.Json.Formatting.None));
    log.AppendLine(name + ": " + cw + "x" + chh + " @(" + bx + "," + by + ")");
  } finally {
    UnityEditor.SceneManagement.EditorSceneManager.ClosePreviewScene(scene);
  }
}
return log.ToString();
