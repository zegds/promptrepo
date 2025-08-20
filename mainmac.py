import threading
import webview
import requests
from app import app
import time
import os
import sys
import signal
import platform

# ------------------ Configuration ------------------
FLASK_PORT = 5003
FLASK_URL = f"http://localhost:{FLASK_PORT}"
CHECK_INTERVAL = 5

# ------------------ Flask Management ------------------
def run_flask():
    app.run(debug=False, port=FLASK_PORT, use_reloader=False)

def start_flask_thread():
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    return flask_thread

def is_flask_alive():
    try:
        r = requests.get(FLASK_URL, timeout=2)
        return r.status_code == 200
    except Exception:
        return False

def watchdog_flask():
    while True:
        if not is_flask_alive():
            print("Flask is down, restarting...")
            start_flask_thread()
        time.sleep(CHECK_INTERVAL)

# ------------------ Shutdown Handling ------------------
def shutdown():
    print("Shutting down...")
    if sys.platform == "win32":
        sys.exit(0)
    else:
        os.kill(os.getpid(), signal.SIGTERM)

# ------------------ Retina Display Fix (macOS) ------------------
def force_redraw(window):
    def _resize():
        time.sleep(1)
        width, height = window.width, window.height
        webview.resize_window(window, width + 1, height + 1)
        webview.resize_window(window, width, height)
    threading.Thread(target=_resize, daemon=True).start()

# ------------------ Main Entry ------------------
if __name__ == '__main__':
    start_flask_thread()
    threading.Thread(target=watchdog_flask, daemon=True).start()
    time.sleep(1)

    window = webview.create_window("Prompt Repository", FLASK_URL, width=1180, height=650)
    force_redraw(window)

    try:
        if platform.system() == 'Darwin':
            webview.start(gui='cocoa')  # macOS native
        else:
            webview.start(gui='edgechromium')  # Windows preferred
    except:
        webview.start(gui='qt')  # Fallback for both
    finally:
        shutdown()

# --- Put near top with your imports ---
from dataclasses import dataclass

# Choose a strategy:
#   "fit_to_monitor" -> keep window ~80% of active monitor's work area
#   "keep_physical_size" -> keep similar physical size by counter-scaling with DPR
RESIZE_STRATEGY = "fit_to_monitor"   # or "keep_physical_size"

BASE_WIDTH, BASE_HEIGHT = 1180, 650   # your preferred base size at DPR=1
SCREEN_COVERAGE = 0.80                # 80% of available work area for fit_to_monitor
MIN_W, MIN_H = 900, 540               # safety minimums

@dataclass
class ScreenInfo:
    dpr: float
    avail_w: int
    avail_h: int
    outer_w: int
    outer_h: int

def compute_target_size(info: ScreenInfo):
    if RESIZE_STRATEGY == "keep_physical_size":
        # Keep physical size: at 2.0 DPR, halve CSS px so it "looks" same physical size
        w = int(max(MIN_W, BASE_WIDTH  / max(info.dpr, 0.5)))
        h = int(max(MIN_H, BASE_HEIGHT / max(info.dpr, 0.5)))
    else:
        # Fit to monitor work area by a fixed coverage %
        w = int(max(MIN_W, info.avail_w * SCREEN_COVERAGE))
        h = int(max(MIN_H, info.avail_h * SCREEN_COVERAGE))

    # Do not exceed available area
    w = min(w, info.avail_w)
    h = min(h, info.avail_h)
    return w, h

class Api:
    def __init__(self, window):
        self.window = window
        self._last_resize = 0

    def update_resolution(self, payload=None):
        """Called from JS periodically and on DPR/screen changes."""
        try:
            dpr = float(payload.get("dpr", 1.0))
            avail_w = int(payload.get("availWidth", 0))
            avail_h = int(payload.get("availHeight", 0))
            outer_w = int(payload.get("outerWidth", 0))
            outer_h = int(payload.get("outerHeight", 0))

            target_w, target_h = compute_target_size(
                ScreenInfo(dpr, avail_w, avail_h, outer_w, outer_h)
            )

            # Only resize if it materially differs (prevents flicker)
            cur_w, cur_h = self.window.width, self.window.height
            if abs(cur_w - target_w) > 2 or abs(cur_h - target_h) > 2:
                webview.resize_window(self.window, target_w, target_h)

        except Exception as e:
            print("update_resolution error:", e)
        return True
DPR_AND_SCREEN_WATCHER = r"""
(function () {
  if (window.__screenWatcherInstalled) return;
  window.__screenWatcherInstalled = true;

  let last = {
    dpr: window.devicePixelRatio || 1,
    aw: screen.availWidth || window.innerWidth,
    ah: screen.availHeight || window.innerHeight
  };

  function payload() {
    return {
      dpr: window.devicePixelRatio || 1,
      availWidth: screen.availWidth || window.innerWidth,
      availHeight: screen.availHeight || window.innerHeight,
      outerWidth: window.outerWidth || window.innerWidth,
      outerHeight: window.outerHeight || window.innerHeight
    };
  }

  async function notify() {
    try {
      if (window.pywebview?.api?.update_resolution) {
        await window.pywebview.api.update_resolution(payload());
      }
    } catch (_) {}
  }

  function maybeNotify() {
    const dpr = window.devicePixelRatio || 1;
    const aw = screen.availWidth || window.innerWidth;
    const ah = screen.availHeight || window.innerHeight;
    if (Math.abs(dpr - last.dpr) > 0.01 || aw !== last.aw || ah !== last.ah) {
      last = { dpr, aw, ah };
      notify();
    }
  }

  // Event-based: DPR and screen changes
  window.addEventListener('resize', maybeNotify, { passive: true });

  // Media query hook for explicit DPR changes
  let mq = window.matchMedia(`(resolution: ${last.dpr}dppx)`);
  function onMQ() { maybeNotify(); remountMQ(); }
  function remountMQ() {
    try { mq.removeEventListener('change', onMQ); } catch(e) {}
    mq = window.matchMedia(`(resolution: ${window.devicePixelRatio || 1}dppx)`);
    try { mq.addEventListener('change', onMQ); } catch(e) {}
  }
  try { mq.addEventListener('change', onMQ); } catch(e) {}

  // Periodic: force check every 20 seconds regardless
  setInterval(maybeNotify, 20000);

  // First paint
  setTimeout(notify, 0);
})();
"""
if __name__ == '__main__':
    start_flask_thread()
    threading.Thread(target=watchdog_flask, daemon=True).start()
    time.sleep(1)

    window = webview.create_window("Prompt Repository", FLASK_URL, width=BASE_WIDTH, height=BASE_HEIGHT)
    api = Api(window)

    # Expose the API method for JS
    window.expose(api.update_resolution)

    # Inject watcher once the DOM is ready
    def _install_js():
        try:
            window.evaluate_js(DPR_AND_SCREEN_WATCHER)
        except Exception as e:
            print("Failed to inject watcher:", e)

    window.events.loaded += _install_js

    # Optional: initial nudge for crispness
    force_redraw(window)

    try:
        if platform.system() == 'Darwin':
            webview.start(gui='cocoa', http_server=True, debug=False, js_api=api)
        else:
            webview.start(gui='edgechromium', http_server=True, debug=False, js_api=api)
    except:
        webview.start(gui='qt', http_server=True, debug=False, js_api=api)
    finally:
        shutdown()
(function () {
  const CHECK_EVERY_MS = 20000; // 20s periodic check
  let baseDPR = window.devicePixelRatio || 1; // for optional physical-size mode
  let lastDPR = baseDPR;

  // Try to “nudge” rendering with no visual change
  function forceRepaint() {
    const root = document.documentElement;
    root.style.willChange = 'transform';
    root.style.transform = 'translateZ(0) scale(1.0001)';
    requestAnimationFrame(() => {
      root.style.transform = '';
      root.style.willChange = '';
    });

    // If host allows it, also try a tiny window resize (often blocked; harmless if so)
    try { window.resizeBy(1, 1); window.resizeBy(-1, -1); } catch (e) {}
  }

  // If you want the UI to keep the same physical size across monitors, uncomment:
  function keepPhysicalSize() {
    const current = window.devicePixelRatio || 1;
    const scale = baseDPR / current;
    const root = document.documentElement;
    root.style.transformOrigin = '0 0';
    root.style.transform = `scale(${scale})`;
    root.style.width  = (100 / scale) + '%';
    root.style.height = (100 / scale) + '%';
  }

  function onDPRChange() {
    const dpr = window.devicePixelRatio || 1;
    if (Math.abs(dpr - lastDPR) > 0.01) {
      lastDPR = dpr;

      // Option A (default): gentle repaint nudge
      forceRepaint();

      // Option B: hard refresh to guarantee re-rasterization
      // location.reload();

      // Option C: keep constant physical size across monitors
      // keepPhysicalSize();
    }
  }

  // React to resizes and explicit DPI media query changes
  window.addEventListener('resize', onDPRChange, { passive: true });

  let mq = window.matchMedia(`(resolution: ${lastDPR}dppx)`);
  function remountMQ() {
    try { mq.removeEventListener('change', onMQ); } catch (e) {}
    mq = window.matchMedia(`(resolution: ${(window.devicePixelRatio || 1)}dppx)`);
    try { mq.addEventListener('change', onMQ); } catch (e) {}
  }
  function onMQ() { onDPRChange(); remountMQ(); }
  try { mq.addEventListener('change', onMQ); } catch (e) {}

  // Periodic safety check (every 20s)
  setInterval(onDPRChange, CHECK_EVERY_MS);

  // Initial pass
  onDPRChange();
})();

