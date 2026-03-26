#!/usr/bin/env python3
import time
import os
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

WATCH_DIR = "/Users/taajirah_systems/.openclaw/workspace/PRDS/"
QUEUE_FILE = "/Users/taajirah_systems/.openclaw/workspace/PRDS/build_queue.json"

class PRDHandler(FileSystemEventHandler):
    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".md"):
            self.add_to_queue(event.src_path)

    def add_to_queue(self, file_path):
        filename = os.path.basename(file_path)
        print(f"[*] New PRD detected: {filename}")
        
        queue = []
        if os.path.exists(QUEUE_FILE):
            try:
                with open(QUEUE_FILE, "r") as f:
                    queue = json.load(f)
            except:
                queue = []
        
        # Avoid duplicates
        if not any(item['file'] == filename for item in queue):
            queue.append({
                "file": filename,
                "status": "pending",
                "detected_at": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            
            with open(QUEUE_FILE, "w") as f:
                json.dump(queue, f, indent=2)
            print(f"[+] Added {filename} to build queue.")

if __name__ == "__main__":
    if not os.path.exists(WATCH_DIR):
        os.makedirs(WATCH_DIR)
        
    event_handler = PRDHandler()
    observer = Observer()
    observer.schedule(event_handler, WATCH_DIR, recursive=False)
    observer.start()
    
    print(f"[*] PRD Watcher started on {WATCH_DIR}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
