import os
import sys
import threading
import time
import webbrowser
from PIL import Image

# Redirect stdout and stderr to devnull to prevent crash in --noconsole mode
if sys.executable.endswith("pythonw.exe") or getattr(sys, 'frozen', False):
    log_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__), "crash.log")
    sys.stdout = open(log_path, 'a')
    sys.stderr = open(log_path, 'a')

# Must be imported after redirection so Werkzeug logging doesn't crash
import pystray
from pystray import MenuItem as item
from server.app import create_app

# Global flag for stopping the server gracefully (Werkzeug doesn't have an easy shutdown hook,
# but since it's running in a daemon thread, closing the tray app will kill it).
flask_thread = None

def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    if getattr(sys, 'frozen', False):
        # In --onedir mode with --add-data "logo (3).ico;.", the logo is in _MEIPASS
        base_path = sys._MEIPASS
    else:
        # In dev mode, assume it's in the project root
        base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

def run_server():
    """ Run the Flask app """
    app = create_app()
    # Disable reloader because it spawns a subprocess which is problematic with pystray and pyinstaller
    app.run(host="0.0.0.0", port=8000, debug=False, use_reloader=False)

def open_browser(icon, item):
    """ Open the admin dashboard in the default browser """
    webbrowser.open("http://127.0.0.1:8000/admin/login")

def exit_action(icon, item):
    """ Exit the application """
    icon.stop()
    # The daemon thread will be killed automatically when main thread exits
    os._exit(0)

def main():
    # Start Flask in a daemon thread
    global flask_thread
    flask_thread = threading.Thread(target=run_server, daemon=True)
    flask_thread.start()

    # Wait a moment for server to start, then open browser
    time.sleep(1.5)
    open_browser(None, None)

    # Setup system tray icon
    icon_path = get_resource_path("logo (3).ico")
    
    try:
        image = Image.open(icon_path)
    except FileNotFoundError:
        # Fallback if image isn't found
        image = Image.new('RGB', (64, 64), color=(0, 0, 0))

    menu = (
        item('Arayüzü Aç', open_browser),
        item('Çıkış', exit_action)
    )

    icon = pystray.Icon("NetKalkan", image, "NetKalkan Server", menu)
    
    # Run the tray icon (blocks until exit_action is called)
    icon.run()

if __name__ == "__main__":
    main()
