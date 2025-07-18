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
