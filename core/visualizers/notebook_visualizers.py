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
