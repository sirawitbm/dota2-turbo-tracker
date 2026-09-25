"""Send a recorded capture to a running Turbo Tracker, as if Dota were live.

Handy for testing without playing. Needs the app (or capture.py) running.

Run:  python replay.py captures/20260925-171154.jsonl [--speed 20]
      --speed 0 sends everything as fast as possible.
"""

import argparse
import json
import time
import urllib.request

from setup_gsi import load_settings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("capture")
    parser.add_argument("--speed", type=float, default=0,
                        help="1 = real time, 20 = 20x faster, 0 = no waiting")
    args = parser.parse_args()

    settings = load_settings()
    url = f"http://127.0.0.1:{settings['port']}/"
    rows = [json.loads(line) for line in open(args.capture, encoding="utf-8")]
    prev = None
    for i, row in enumerate(rows, 1):
        if args.speed and prev is not None:
            time.sleep(max(0, row["received"] - prev) / args.speed)
        prev = row["received"]
        data = dict(row["data"], auth={"token": settings["token"]})
        req = urllib.request.Request(url, data=json.dumps(data).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=5).close()
        if i % 200 == 0:
            print(f"  {i}/{len(rows)} sent")
    print(f"Done: {len(rows)} messages sent.")


if __name__ == "__main__":
    main()
