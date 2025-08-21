<<<<<<< HEAD
"""
process_viewer_widget.py
A lightweight Jupyter/Colab-compatible anywidget for visualizing BPMN/DMN
(diagram-only) with click → Python and element highlighting from Python.

Requirements (install once):
    pip install anywidget ipywidgets

Usage:
    from process_viewer_widget import ProcessViewerWidget

    w = ProcessViewerWidget(mode="bpmn", xml=bpmn_xml, height=480)
    display(w)

    # Get last clicked element id (BPMN & DMN-DRD):
    def on_click(change):
        print("clicked:", change["new"])
    w.observe(on_click, names=["clicked_id"])

    # Highlight elements (BPMN & DMN-DRD):
    w.highlight_ids = ["Task_123", "Gateway_9"]

    # Clear highlights:
    w.highlight_ids = []

    # Switch modes or XML at any time:
    w.mode = "dmn"
    w.xml = dmn_xml
"""

import anywidget
import traitlets as T


class ProcessViewerWidget(anywidget.AnyWidget):
    """
    BPMN/DMN process viewer (read-only) using bpmn.io/dmn.io via CDN.

    Features:
    - Render BPMN *or* DMN (DRD / decision table / literal expression).
    - Click an element → Python `clicked_id` updates (BPMN & DMN-DRD).
    - Python-controlled highlighting via `highlight_ids` (BPMN & DMN-DRD).
    - Adjustable height.

    Notes:
    - For DMN decision tables / literal expressions, canvas clicks are not available.
    - Highlighting only applies to canvas-based views (BPMN & DMN-DRD).
    """

    # Frontend (ESM) code injected by anywidget
    _esm = r"""
    export function render({ model, el }) {
      // Base markup + minimal styles
      el.innerHTML = `
        <style>
          .pv-wrap {
            border: 1px solid #e5e7eb;
            border-radius: 10px;
            overflow: hidden;
            font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif;
          }
          .pv-toolbar {
            display: flex; gap: 8px; align-items: center;
            padding: 6px 8px; background: #f8fafc; border-bottom: 1px solid #e5e7eb;
          }
          .pv-toolbar button {
            border: 1px solid #e5e7eb; background: white; border-radius: 8px;
            padding: 4px 10px; cursor: pointer;
          }
          .pv-status { margin-left: 8px; font-size: 12px; color: #64748b; }
          .pv-container { width: 100%; height: 520px; }
          .pv-mode { font-weight: 600; }

          /* Highlight markers for BPMN/DMN DRD via canvas.addMarker(id, 'pv-highlight') */
          .djs-shape.pv-highlight .djs-visual > * { stroke: #10b981 !important; stroke-width: 3 !important; }
          .djs-connection.pv-highlight .djs-visual > * { stroke: #10b981 !important; stroke-width: 3 !important; }

          /* Optional: subtle dim for non-highlighted (not applied by default)
          .pv-dim-all .djs-element .djs-visual > * { opacity: 0.35; }
          .pv-dim-all .djs-element.pv-highlight .djs-visual > * { opacity: 1; }
          */
        </style>

        <div class="pv-wrap">
          <div class="pv-toolbar">
            <strong class="pv-mode" id="pv-mode">—</strong>
            <button id="pv-fit"  title="Fit to viewport">Fit</button>
            <button id="pv-zin"  title="Zoom in">Zoom +</button>
            <button id="pv-zout" title="Zoom out">Zoom −</button>
            <span class="pv-status" id="pv-status">Ready</span>
          </div>
          <div class="pv-container" id="pv-container"></div>
        </div>
      `;

      const container = el.querySelector("#pv-container");
      const statusEl  = el.querySelector("#pv-status");
      const modeEl    = el.querySelector("#pv-mode");
      const fitBtn    = el.querySelector("#pv-fit");
      const zinBtn    = el.querySelector("#pv-zin");
      const zoutBtn   = el.querySelector("#pv-zout");

      // State
      let currentMode = null;  // "bpmn" | "dmn"
      let bpmnViewer  = null;  // window.BpmnJS instance
      let dmnViewer   = null;  // window.DmnJS instance
      let highlighted = new Set(); // currently highlighted ids applied to canvas

      // Helpers
      function setStatus(msg) { statusEl.textContent = msg; }

      function loadScript(src) {
        return new Promise((resolve, reject) => {
          const s = document.createElement("script");
          s.src = src; s.onload = resolve; s.onerror = reject;
          document.head.appendChild(s);
        });
      }

      async function ensureLibs(mode) {
        // Styles first (once)
        if (!document.querySelector('link[data-pv="bpmn-css"]')) {
          const l1 = document.createElement("link");
          l1.rel = "stylesheet";
          l1.href = "https://unpkg.com/bpmn-js@10.5.0/dist/assets/bpmn-js.css";
          l1.setAttribute("data-pv","bpmn-css");
          document.head.appendChild(l1);
        }
        if (!document.querySelector('link[data-pv="dmn-css"]')) {
          for (const href of [
            "https://unpkg.com/dmn-js@14.8.1/dist/assets/diagram-js.css",
            "https://unpkg.com/dmn-js@14.8.1/dist/assets/dmn-font/css/dmn.css",
            "https://unpkg.com/dmn-js@14.8.1/dist/dmn-js.css"
          ]) {
            const l = document.createElement("link");
            l.rel = "stylesheet"; l.href = href; l.setAttribute("data-pv","dmn-css");
            document.head.appendChild(l);
          }
        }
        // Scripts
        if (mode === "bpmn" && !window.BpmnJS) {
          await loadScript("https://unpkg.com/bpmn-js@10.5.0/dist/bpmn-viewer.production.min.js");
        }
        if (mode === "dmn" && !window.DmnJS) {
          await loadScript("https://unpkg.com/dmn-js@14.8.1/dist/dmn-viewer.production.min.js");
        }
      }

      function getCanvasAndEventBus() {
        if (currentMode === "bpmn" && bpmnViewer) {
          return { canvas: bpmnViewer.get("canvas"), eventBus: bpmnViewer.get("eventBus"), viewer: bpmnViewer };
        }
        if (currentMode === "dmn" && dmnViewer) {
          const activeView   = dmnViewer.getActiveView();
          const activeViewer = dmnViewer.getActiveViewer();
          if (activeView && activeView.type === "drd") {
            return { canvas: activeViewer.get("canvas"), eventBus: activeViewer.get("eventBus"), viewer: activeViewer };
          }
        }
        return { canvas: null, eventBus: null, viewer: null };
      }

      function clearHighlights() {
        const { canvas, viewer } = getCanvasAndEventBus();
        if (!canvas) return;
        const elementRegistry = viewer.get("elementRegistry");
        for (const id of highlighted) {
          const el = elementRegistry.get(id);
          if (el) canvas.removeMarker(el, "pv-highlight");
        }
        highlighted.clear();
      }

      function applyHighlights(ids) {
        const { canvas, viewer } = getCanvasAndEventBus();
        if (!canvas || !viewer) return;

        // Remove any previous markers not in the new set
        const next = new Set(Array.isArray(ids) ? ids : []);
        const elementRegistry = viewer.get("elementRegistry");

        for (const id of highlighted) {
          if (!next.has(id)) {
            const el = elementRegistry.get(id);
            if (el) canvas.removeMarker(el, "pv-highlight");
          }
        }
        // Add new markers
        for (const id of next) {
          const el = elementRegistry.get(id);
          if (el) canvas.addMarker(el, "pv-highlight");
        }
        highlighted = next;
      }

      async function renderXML() {
        const xml    = model.get("xml") || "";
        const mode   = model.get("mode") || "bpmn";
        const height = model.get("height") || 520;

        container.style.height = `${height}px`;
        modeEl.textContent = mode.toUpperCase();
        setStatus("Loading…");

        if (!xml.trim()) {
          container.innerHTML = `<div style="padding:12px;color:#64748b;">Provide XML</div>`;
          setStatus("Waiting for XML");
          // Disable toolbar since there's nothing to act on
          fitBtn.disabled = zinBtn.disabled = zoutBtn.disabled = true;
          return;
        }

        await ensureLibs(mode);

        // Mode switch → destroy previous viewer
        if (mode !== currentMode) {
          if (bpmnViewer) { bpmnViewer.destroy(); bpmnViewer = null; }
          if (dmnViewer)  { dmnViewer.destroy();  dmnViewer  = null; }
          container.innerHTML = "";
          currentMode = mode;
        }

        try {
          if (mode === "bpmn") {
            if (!bpmnViewer) {
              bpmnViewer = new window.BpmnJS({ container });
            }
            const res = await bpmnViewer.importXML(xml);
            const { canvas, eventBus } = getCanvasAndEventBus();

            canvas.zoom("fit-viewport");
            fitBtn.disabled = zinBtn.disabled = zoutBtn.disabled = false;

            // Wire click events
            eventBus.off("element.click");
            eventBus.on("element.click", (e) => {
              const id = e?.element?.id || null;
              model.set("clicked_id", id);
              model.save_changes();
            });

            // Apply existing highlights from Python
            applyHighlights(model.get("highlight_ids"));

            // Toolbar actions
            fitBtn.onclick  = () => canvas.zoom("fit-viewport");
            zinBtn.onclick  = () => canvas.zoom(canvas.zoom() + 0.2);
            zoutBtn.onclick = () => canvas.zoom(canvas.zoom() - 0.2);

            setStatus(res?.warnings?.length ? `Loaded with ${res.warnings.length} warning(s)` : "Loaded");
          } else {
            if (!dmnViewer) {
              dmnViewer = new window.DmnJS({ container });
            }
            await dmnViewer.importXML(xml);
            const activeView = dmnViewer.getActiveView();
            const activeViewer = dmnViewer.getActiveViewer();

            if (activeView && activeView.type === "drd") {
              const { canvas, eventBus } = getCanvasAndEventBus();
              canvas.zoom("fit-viewport");
              fitBtn.disabled = zinBtn.disabled = zoutBtn.disabled = false;

              // Clicks for DRD
              eventBus.off("element.click");
              eventBus.on("element.click", (e) => {
                const id = e?.element?.id || null;
                model.set("clicked_id", id);
                model.save_changes();
              });

              // Apply highlights
              applyHighlights(model.get("highlight_ids"));

              // Toolbar actions
              fitBtn.onclick  = () => canvas.zoom("fit-viewport");
              zinBtn.onclick  = () => canvas.zoom(canvas.zoom() + 0.2);
              zoutBtn.onclick = () => canvas.zoom(canvas.zoom() - 0.2);

              setStatus("Loaded (DRD)");
            } else {
              // Decision table / literal expression: no canvas → disable toolbar and highlighting
              fitBtn.disabled = zinBtn.disabled = zoutBtn.disabled = true;
              clearHighlights();
              model.set("clicked_id", null);
              model.save_changes();
              setStatus("Loaded (table/text)");
            }
          }
        } catch (err) {
          container.innerHTML = `<pre style="color:#b91c1c">${(err && err.message) || err}</pre>`;
          setStatus("Import error");
        }
      }

      // React to Python-side changes
      model.on("change:xml", renderXML);
      model.on("change:mode", renderXML);
      model.on("change:height", renderXML);

      model.on("change:highlight_ids", () => {
        // Re-apply without reimporting
        applyHighlights(model.get("highlight_ids"));
      });

      // Initial render
      renderXML();
    }
    """

    # Public, synced properties
    xml = T.Unicode("").tag(sync=True)
    mode = T.Enum(values=["bpmn", "dmn"], default_value="bpmn").tag(sync=True)
    height = T.Int(520).tag(sync=True)

    # Last clicked element id (BPMN & DMN-DRD). None if nothing selected or non-canvas view.
    clicked_id = T.Unicode(allow_none=True, default_value=None).tag(sync=True)

    # List of element IDs to highlight on the canvas (BPMN & DMN-DRD).
    highlight_ids = T.List(T.Unicode(), default_value=[]).tag(sync=True)


class BpmnViewerWidget(ProcessViewerWidget):
  """Simple BPMN-only viewer widget with convenient defaults.

  Usage:
    w = BpmnViewerWidget(xml=bpmn_xml, height=480)
    display(w)
  """
  def __init__(self, xml: str = "", height: int = 520, **kwargs):
    # Set defaults before calling super so traitlets are initialized
    kwargs.setdefault('mode', 'bpmn')
    kwargs.setdefault('xml', xml)
    kwargs.setdefault('height', height)
    super().__init__(**kwargs)


class DmnViewerWidget(ProcessViewerWidget):
  """Simple DMN viewer widget (DRD / tables) with convenient defaults.

  Usage:
    w = DmnViewerWidget(xml=dmn_xml, height=480)
    display(w)
  """
  def __init__(self, xml: str = "", height: int = 520, **kwargs):
    kwargs.setdefault('mode', 'dmn')
    kwargs.setdefault('xml', xml)
    kwargs.setdefault('height', height)
    super().__init__(**kwargs)
=======


from __future__ import annotations

import anywidget
import traitlets as T
from pathlib import Path
import base64

"""# 1) one-time: fetch vendor assets (writes to ./vendor next to this file)
from process_viewer_widget import install_vendor_assets
install_vendor_assets()  # needs internet just once

# 2) use the widget
from process_viewer_widget import ProcessViewerWidget
w = ProcessViewerWidget(mode="bpmn", xml=bpmn_xml, height=460)
display(w)
w.highlight_ids = ["Task_1", "Flow_2"]
def on_click(change): print("clicked:", change["new"])
w.observe(on_click, names=["clicked_id"])

Notes
-----
- Highlighting & clicks apply to BPMN and DMN-DRD (diagram canvas views). DMN tables/text have no canvas.
- If you want to pin different versions, edit URLS in install_vendor_assets().
"""

import urllib.request, urllib.error

import re

def _download_with_mirrors(urls: list[str], out: Path):
    last_err = None
    for u in urls:
        try:
            with urllib.request.urlopen(u) as r, open(out, "wb") as f:
                f.write(r.read())
            print(f"✓ {out.name}  ←  {u}")
            return
        except Exception as e:
            last_err = e
            print(f"… {out.name} failed at {u}: {e}")
    raise RuntimeError(f"Failed to download {out.name} from mirrors. Last error: {last_err}")

def install_vendor_assets(dest: Path | None = None) -> Path:
    """
    Vendor bpmn-js & dmn-js viewer bundles + CSS (and DMN fonts) into ./vendor.
    Uses versionless jsDelivr → unpkg mirrors and correct split CSS for dmn-js.
    """
    here = Path(__file__).resolve().parent
    vendor = (dest or here / "vendor")
    vendor.mkdir(parents=True, exist_ok=True)

    def mirrors(p: str) -> list[str]:
        return [f"https://cdn.jsdelivr.net/npm/{p}", f"https://unpkg.com/{p}"]

    files: dict[str, list[str]] = {
        # BPMN: viewer + CSS
        "bpmn-viewer.production.min.js": mirrors("bpmn-js/dist/bpmn-viewer.production.min.js"),
        "bpmn-js.css": mirrors("bpmn-js/dist/assets/bpmn-js.css"),

        # DMN: viewer JS
        "dmn-viewer.production.min.js": mirrors("dmn-js/dist/dmn-viewer.production.min.js"),

        # DMN: split CSS (no single dmn-js.css anymore)
        "diagram-js.css": mirrors("dmn-js/dist/assets/diagram-js.css"),
        "dmn-js-shared.css": mirrors("dmn-js/dist/assets/dmn-js-shared.css"),
        "dmn-js-drd.css": mirrors("dmn-js/dist/assets/dmn-js-drd.css"),
        "dmn-js-decision-table.css": mirrors("dmn-js/dist/assets/dmn-js-decision-table.css"),
        "dmn-js-decision-table-controls.css": mirrors("dmn-js/dist/assets/dmn-js-decision-table-controls.css"),
        "dmn-js-literal-expression.css": mirrors("dmn-js/dist/assets/dmn-js-literal-expression.css"),
        "dmn-js-boxed-expression.css": mirrors("dmn-js/dist/assets/dmn-js-boxed-expression.css"),
        "dmn-js-boxed-expression-controls.css": mirrors("dmn-js/dist/assets/dmn-js-boxed-expression-controls.css"),

        # DMN fonts + font CSS
        "dmn.css": mirrors("dmn-js/dist/assets/dmn-font/css/dmn.css"),
        "dmn-embedded.css": mirrors("dmn-js/dist/assets/dmn-font/css/dmn-embedded.css"),
        "dmn-codes.css": mirrors("dmn-js/dist/assets/dmn-font/css/dmn-codes.css"),
        "dmn-font.woff2": mirrors("dmn-js/dist/assets/dmn-font/font/dmn.woff2"),
        "dmn-font.woff":  mirrors("dmn-js/dist/assets/dmn-font/font/dmn.woff"),
        "dmn-font.ttf":   mirrors("dmn-js/dist/assets/dmn-font/font/dmn.ttf"),
        "dmn-font.eot":   mirrors("dmn-js/dist/assets/dmn-font/font/dmn.eot"),
        "dmn-font.svg":   mirrors("dmn-js/dist/assets/dmn-font/font/dmn.svg"),
    }

    for name, urls in files.items():
        out = vendor / name
        if out.exists() and out.stat().st_size > 0:
            continue
        print(f"Downloading {name} …")
        _download_with_mirrors(urls, out)

    # Patch font urls inside dmn font css files to reference sibling files (no 'font/' subdir)
    for css_name in ("dmn.css", "dmn-embedded.css"):
        css_path = vendor / css_name
        if not css_path.exists():
            continue
        css = css_path.read_text(encoding="utf-8")
        css = re.sub(r"url\\(['\\\"]?font/dmn(\\.[^'\"\\)#]+)(#[^'\"\\)]*)?['\\\"]?\\)",
                     r"url('./dmn-font\\1\\2')", css)
        css_path.write_text(css, encoding="utf-8")

    print(f"Assets ready in: {vendor}")
    return vendor
  
  
import anywidget
import traitlets as T
from pathlib import Path
import base64

class ProcessViewerWidget(anywidget.AnyWidget):
    """
    BPMN/DMN viewer for notebooks (VS Code/Jupyter/Colab) with:
      - click -> Python (clicked_id)
      - Python-driven highlighting (highlight_ids)
      - zero-network assets
      - CSP-safe loading (JS via blob URLs; fonts via data URIs)

    Prereq: run install_vendor_assets() once to create ./vendor with bpmn/dmn files.
    """

    # -------- synced props (Python -> front-end) --------
    xml = T.Unicode("").tag(sync=True)
    mode = T.Enum(values=["bpmn", "dmn"], default_value="bpmn").tag(sync=True)
    height = T.Int(520).tag(sync=True)
    clicked_id = T.Unicode(allow_none=True, default_value=None).tag(sync=True)
    highlight_ids = T.List(T.Unicode(), default_value=[]).tag(sync=True)

    # asset payloads (strings / base64) — populated in __init__
    bpmn_js = T.Unicode("").tag(sync=True)
    bpmn_css = T.Unicode("").tag(sync=True)

    dmn_js = T.Unicode("").tag(sync=True)
    dmn_css_all = T.Unicode("").tag(sync=True)  # shared + drd + decision + boxed + controls + diagram

    # DMN fonts as base64 (embedded into CSS as data URIs)
    dmn_font_woff2_b64 = T.Unicode("").tag(sync=True)
    dmn_font_woff_b64  = T.Unicode("").tag(sync=True)
    dmn_font_ttf_b64   = T.Unicode("").tag(sync=True)
    dmn_font_eot_b64   = T.Unicode("").tag(sync=True)
    dmn_font_svg_b64   = T.Unicode("").tag(sync=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        v = Path(__file__).resolve().parent / "vendor"
        # JS
        self.bpmn_js = (v / "bpmn-viewer.production.min.js").read_text(encoding="utf-8")
        self.dmn_js  = (v / "dmn-viewer.production.min.js").read_text(encoding="utf-8")

        # CSS: BPMN single; DMN split (concat in a stable order)
        self.bpmn_css = (v / "bpmn-js.css").read_text(encoding="utf-8")
        dmn_parts = [
            "diagram-js.css",
            "dmn-js-shared.css",
            "dmn-js-drd.css",
            "dmn-js-decision-table.css",
            "dmn-js-decision-table-controls.css",
            "dmn-js-literal-expression.css",
            "dmn-js-boxed-expression.css",
            "dmn-js-boxed-expression-controls.css",
        ]
        self.dmn_css_all = "\n/* ---- */\n".join((v / p).read_text(encoding="utf-8") for p in dmn_parts)

        # Fonts -> base64
        def b64(p): return base64.b64encode((v / p).read_bytes()).decode("ascii")
        self.dmn_font_woff2_b64 = b64("dmn-font.woff2")
        self.dmn_font_woff_b64  = b64("dmn-font.woff")
        self.dmn_font_ttf_b64   = b64("dmn-font.ttf")
        self.dmn_font_eot_b64   = b64("dmn-font.eot")
        self.dmn_font_svg_b64   = b64("dmn-font.svg")

    # -------- front-end (CSP-safe) --------
    _esm = r"""
export function render({ model, el }) {
  el.innerHTML = `
    <style>
      .pv-wrap { border:1px solid #e5e7eb; border-radius:10px; overflow:hidden;
                 font-family: system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif; }
      .pv-toolbar { display:flex; gap:8px; align-items:center; padding:6px 8px;
                    background:#f8fafc; border-bottom:1px solid #e5e7eb; }
      .pv-toolbar button { border:1px solid #e5e7eb; background:#fff; border-radius:8px;
                           padding:4px 10px; cursor:pointer; }
      .pv-status { margin-left:8px; font-size:12px; color:#64748b; }
      .pv-iframe { width:100%; height:520px; border:0; background:#fff; display:block; }
      .pv-mode { font-weight:600; }
    </style>
    <div class="pv-wrap">
      <div class="pv-toolbar">
        <strong class="pv-mode" id="pv-mode">—</strong>
        <button id="pv-fit">Fit</button>
        <button id="pv-zin">Zoom +</button>
        <button id="pv-zout">Zoom −</button>
        <span class="pv-status" id="pv-status">Booting…</span>
      </div>
      <iframe class="pv-iframe" id="pv-frame" sandbox="allow-scripts allow-same-origin"></iframe>
    </div>
  `;

  const frame = el.querySelector("#pv-frame");
  const statusEl = el.querySelector("#pv-status");
  const modeEl = el.querySelector("#pv-mode");
  const fitBtn = el.querySelector("#pv-fit");
  const zinBtn = el.querySelector("#pv-zin");
  const zoutBtn = el.querySelector("#pv-zout");

  function setStatus(m){ statusEl.textContent = m; }

  // Build a complete HTML doc as a Blob and set iframe.src to the blob URL
  function buildFrameHtml() {
    const bpmnJS   = model.get("bpmn_js");   // JS text
    const bpmnCSS  = model.get("bpmn_css");  // CSS text
    const dmnJS    = model.get("dmn_js");    // JS text
    const dmnCSS   = model.get("dmn_css_all"); // CSS text

    // Minimal font face (already embedded via our base64 sync fields)
    const fontCSS = `
@font-face {
  font-family: 'dmn';
  src: url(data:application/vnd.ms-fontobject;base64,${model.get("dmn_font_eot_b64")});
  src:
    url(data:font/woff2;base64,${model.get("dmn_font_woff2_b64")}) format('woff2'),
    url(data:font/woff;base64,${model.get("dmn_font_woff_b64")}) format('woff'),
    url(data:font/ttf;base64,${model.get("dmn_font_ttf_b64")}) format('truetype'),
    url(data:image/svg+xml;base64,${model.get("dmn_font_svg_b64")}) format('svg');
  font-weight: normal; font-style: normal; font-display: swap;
}
`;

    // The iframe page wires postMessage <-> parent for click + toolbar actions + highlight API
    return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8" />
<style>
  html, body { margin:0; padding:0; height:100%; }
  #container { height:100%; width:100%; }
  ${bpmnCSS}
  ${fontCSS}
  ${dmnCSS}
  /* highlight style */
  .djs-shape.pv-highlight .djs-visual > * { stroke:#10b981 !important; stroke-width:3 !important; }
  .djs-connection.pv-highlight .djs-visual > * { stroke:#10b981 !important; stroke-width:3 !important; }
</style>
</head>
<body>
  <div id="container"></div>
  <script>${bpmnJS}</script>
  <script>${dmnJS}</script>
  <script>
  (function(){
    let viewerBpmn = null;
    let viewerDmn  = null;
    let currentMode = null;
    let highlighted = new Set();

    function getCanvasAndBus(){
      if (currentMode === "bpmn" && viewerBpmn) {
        return { canvas: viewerBpmn.get("canvas"), bus: viewerBpmn.get("eventBus"), reg: viewerBpmn.get("elementRegistry") };
      }
      if (currentMode === "dmn" && viewerDmn) {
        const av = viewerDmn.getActiveView();
        const aw = viewerDmn.getActiveViewer();
        if (av && av.type === "drd") return { canvas: aw.get("canvas"), bus: aw.get("eventBus"), reg: aw.get("elementRegistry") };
      }
      return { canvas:null, bus:null, reg:null };
    }

    function clearHighlights(){
      const {canvas, reg} = getCanvasAndBus();
      if (!canvas || !reg) return;
      for (const id of highlighted){
        const el = reg.get(id);
        if (el) canvas.removeMarker(el, "pv-highlight");
      }
      highlighted.clear();
    }
    function applyHighlights(ids){
      const {canvas, reg} = getCanvasAndBus();
      if (!canvas || !reg) return;
      const next = new Set(Array.isArray(ids)? ids: []);
      for (const id of highlighted){
        if (!next.has(id)){ const el = reg.get(id); if (el) canvas.removeMarker(el, "pv-highlight"); }
      }
      for (const id of next){
        const el = reg.get(id); if (el) canvas.addMarker(el, "pv-highlight");
      }
      highlighted = next;
    }

    async function render({mode, xml, fit}){
      const container = document.getElementById("container");
      if (!xml || !xml.trim()){
        container.innerHTML = "<div style='padding:12px;color:#64748b;'>Provide XML</div>";
        return;
      }
      if (mode !== currentMode){
        if (viewerBpmn) { viewerBpmn.destroy(); viewerBpmn = null; }
        if (viewerDmn)  { viewerDmn.destroy();  viewerDmn  = null; }
        container.innerHTML = "";
        currentMode = mode;
      }
      if (mode === "bpmn"){
        if (!viewerBpmn) viewerBpmn = new window.BpmnJS({container});
        try {
          const res = await viewerBpmn.importXML(xml);
          const c = viewerBpmn.get("canvas");
          const bus = viewerBpmn.get("eventBus");
          if (fit) c.zoom("fit-viewport");
          bus.off("element.click");
          bus.on("element.click", e => {
            const id = e && e.element && e.element.id || null;
            parent.postMessage({ _pv:true, type:"clicked", id }, "*");
          });
          parent.postMessage({ _pv:true, type:"status", msg: res && res.warnings && res.warnings.length ? "Loaded with warnings" : "Loaded" },"*");
        } catch (err) {
          container.innerHTML = "<pre style='color:#b91c1c'>" + (err && err.message || err) + "</pre>";
          parent.postMessage({ _pv:true, type:"status", msg:"Import error" },"*");
        }
      } else {
        if (!viewerDmn) viewerDmn = new window.DmnJS({container});
        try {
          await viewerDmn.importXML(xml);
          const av = viewerDmn.getActiveView();
          const aw = viewerDmn.getActiveViewer();
          if (av && av.type === "drd"){
            const c = aw.get("canvas");
            const bus = aw.get("eventBus");
            if (fit) c.zoom("fit-viewport");
            bus.off("element.click");
            bus.on("element.click", e => {
              const id = e && e.element && e.element.id || null;
              parent.postMessage({ _pv:true, type:"clicked", id },"*");
            });
            parent.postMessage({ _pv:true, type:"status", msg:"Loaded (DRD)" },"*");
          } else {
            parent.postMessage({ _pv:true, type:"status", msg:"Loaded (table/text)" },"*");
          }
        } catch (err) {
          container.innerHTML = "<pre style='color:#b91c1c'>" + (err && err.message || err) + "</pre>";
          parent.postMessage({ _pv:true, type:"status", msg:"Import error" },"*");
        }
      }
      // apply any existing highlights
      applyHighlights(window.__pv_highlight || []);
    }

    // messages from parent
    window.addEventListener("message", (ev) => {
      const m = ev.data || {};
      if (!m || !m._pv) return;
      if (m.type === "render") render(m);
      if (m.type === "fit")   { const {canvas} = getCanvasAndBus(); if (canvas) canvas.zoom("fit-viewport"); }
      if (m.type === "zoom")  { const {canvas} = getCanvasAndBus(); if (canvas) { const z=canvas.zoom(); canvas.zoom(z + (m.step||0.2)); } }
      if (m.type === "highlight"){ window.__pv_highlight = m.ids || []; applyHighlights(window.__pv_highlight); }
    });
  })();
  </script>
</body>
</html>`;
  }

  // create blob URL and load iframe
  function loadFrame() {
    const html = buildFrameHtml();
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    frame.onload = () => { URL.revokeObjectURL(url); };
    frame.src = url;
  }

  // parent <-> iframe helpers
  function postToFrame(msg){
    frame.contentWindow && frame.contentWindow.postMessage({ _pv:true, ...msg }, "*");
  }

  // receive click/status from iframe
  function onMsg(ev){
    const d = ev.data || {};
    if (!d || !d._pv) return;
    if (d.type === "clicked"){
      model.set("clicked_id", d.id || null);
      model.save_changes();
    }
    if (d.type === "status"){
      setStatus(d.msg || "");
    }
  }
  window.addEventListener("message", onMsg);

  // Wire toolbar
  fitBtn.onclick  = () => postToFrame({ type:"fit" });
  zinBtn.onclick  = () => postToFrame({ type:"zoom", step: +0.2 });
  zoutBtn.onclick = () => postToFrame({ type:"zoom", step: -0.2 });

  // React to model changes
  function rerender(){
    const mode = model.get("mode") || "bpmn";
    const xml  = model.get("xml")  || "";
    const h    = model.get("height") || 520;
    frame.style.height = `${h}px`;
    modeEl.textContent = mode.toUpperCase();
    postToFrame({ type:"render", mode, xml, fit:true });
  }
  model.on("change:xml", rerender);
  model.on("change:mode", rerender);
  model.on("change:height", rerender);
  model.on("change:highlight_ids", () => {
    postToFrame({ type:"highlight", ids: model.get("highlight_ids") || [] });
  });

  // boot sequence
  loadFrame();
  // small delay so iframe is ready to receive the first message
  setTimeout(rerender, 30);
}
    """


# Convenience subclasses: one-widget-per-diagram-type
class BPMNViewerWidget(ProcessViewerWidget):
  """BPMN-only notebook visualizer (mode fixed to 'bpmn')."""
  mode = T.Enum(values=["bpmn"], default_value="bpmn").tag(sync=True)


class DMNViewerWidget(ProcessViewerWidget):
  """DMN-only notebook visualizer (mode fixed to 'dmn')."""
  mode = T.Enum(values=["dmn"], default_value="dmn").tag(sync=True)