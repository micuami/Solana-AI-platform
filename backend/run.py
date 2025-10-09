import os
import webbrowser
from threading import Timer
from backend.main import create_app
from backend.configuration_classes_for_flask import DevConfig

if __name__ == '__main__':
    port = 5001
    url = f"http://127.0.0.1:{port}/"

    def open_browser():
        webbrowser.open(url)

    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        Timer(1, open_browser).start()

    app = create_app(DevConfig)
    app.run(debug=True, host="0.0.0.0", port=port)