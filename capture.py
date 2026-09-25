"""Record every raw message Dota sends, so we can see the real data.

Run this, then play one Turbo game. Each message is saved as one line in
captures/<date-time>.jsonl. Stop with Ctrl+C.

Run:  python capture.py
"""

import json
import sys
import time
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SETTINGS = HERE / "local" / "settings.json"   # source runs only
CAPTURES = HERE / "captures"


def load_settings():
    if not SETTINGS.exists():
        sys.exit("No local/settings.json yet. Run  python setup_gsi.py  first.")
    return json.loads(SETTINGS.read_text(encoding="utf-8"))


class Handler(BaseHTTPRequestHandler):
    token = ""
    out = None
    count = 0
    last_state = None

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body)
        except ValueError:
            self.send_response(400)
            self.end_headers()
            return

        # Ignore anything that doesn't carry our secret token.
        if data.get("auth", {}).get("token") != Handler.token:
            self.send_response(403)
            self.end_headers()
            return
        data.pop("auth", None)

        record = {"received": time.time(), "data": data}
        Handler.out.write(json.dumps(record) + "\n")
        Handler.out.flush()
        Handler.count += 1

        state = data.get("map", {}).get("game_state")
        if state != Handler.last_state:
            print(f"[{datetime.now():%H:%M:%S}] game state -> {state}")
            Handler.last_state = state
        elif Handler.count % 50 == 0:
            print(f"  ...{Handler.count} messages saved")

        self.send_response(200)
        self.end_headers()

    def log_message(self, *args):
        pass  # keep the terminal quiet


def main():
    settings = load_settings()
    CAPTURES.mkdir(exist_ok=True)
    path = CAPTURES / f"{datetime.now():%Y%m%d-%H%M%S}.jsonl"
    Handler.token = settings["token"]
    Handler.out = path.open("w", encoding="utf-8")

    server = HTTPServer(("127.0.0.1", settings["port"]), Handler)
    print(f"Listening on 127.0.0.1:{settings['port']}")
    print(f"Saving to {path}")
    print("Start Dota and play a Turbo game. Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        Handler.out.close()
        print(f"\nStopped. {Handler.count} messages saved to {path}")


if __name__ == "__main__":
    main()
