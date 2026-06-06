"""Run before tkinter loads in frozen builds (avoids OneDrive/temp extraction issues)."""
import os
import sys

if getattr(sys, "frozen", False):
    cache = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "cursor-usage-tray", "cache")
    os.makedirs(cache, exist_ok=True)
    os.environ["TEMP"] = cache
    os.environ["TMP"] = cache
