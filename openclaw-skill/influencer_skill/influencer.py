import os
import json
import time
import datetime
import requests
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

KNOWLEDGE_BASE = "/Users/taajirah_systems/.openclaw/workspace/knowledge_base/"
QUEUED_CONTENT = "/Users/taajirah_systems/.openclaw/workspace/knowledge_base/content_queue.json"

class InfluencerHandler(FileSystemEventHandler):
    def __init__(self):
        super().__init__()
        self.technical_count = 0
        self.social_count = 0
        self.hub_url = "http://localhost:3001/api/agents/a5"
        self._report_status("idle", "Awaiting new findings...")

    def _report_status(self, status, task):
        try:
            requests.post(self.hub_url, json={
                "status": status,
                "currentTask": task,
                "name": "Nova",
                "role": "Research Assistant",
                "color": "#ec4899"
            }, timeout=2)
        except Exception as e:
            print(f"[!] Federation Hub report failed: {e}")

    def on_created(self, event):
        if not event.is_directory and event.src_path.endswith(".txt"):
            self.process_finding(event.src_path)

    def process_finding(self, file_path):
        filename = os.path.basename(file_path)
        print(f"[*] New finding detected for AI Influencer: {filename}")
        self._report_status("working", f"Analyzing: {filename}")
        with open(file_path, "r") as f:
            finding_text = f.read()
        
        # Determine content type (Heuristic: keywords for technical vs social)
        is_technical = any(word in finding_text.lower() for word in ["sentinel", "security", "audit", "protocol", "architecture"])
        
        # 70/30 Schedule Enforcement
        if is_technical:
            self.technical_count += 1
            content_type = "technical"
        else:
            # ROI Check for Social Content
            if not self._perform_roi_check(finding_text):
                print(f"[-] Social content '{filename}' failed ROI Check. Skipping.")
                return
            self.social_count += 1
            content_type = "social"

        # Polyglot Diplomacy Logic
        language = self._detect_target_cluster_language(finding_text)
        
        script = self.generate_script(finding_text, content_type, language)
        self.queue_for_approval(filename, script, content_type)
        self._report_status("thinking", f"Waiting for approval: {filename}")

    def _perform_roi_check(self, text):
        """
        CEO Logic: Evaluate brand alignment and ROI before social engagement.
        """
        print("[*] ROI CHECK: Evaluating social engagement value...")
        # Simulation: High-status agents are worth the ROI
        if "leaderboard" in text.lower() or "game" in text.lower():
            return "analytics_report" in text.lower() # Only join if they provide analytics
        return True # Default social engagement is OK unless suspicious

    def _detect_target_cluster_language(self, text):
        if "français" in text.lower() or "cluster:eu" in text.lower():
            return "fr"
        return "en"

    def generate_script(self, text, content_type, language="en"):
        # Simulation of NotebookLM distillation with CEO persona
        if language == "fr":
            hook = f"ACCROCHE: Saviez-vous que {text[:50]}...?"
            body = "CORPS: Cela change tout pour la structure Sovereign."
            cta = "APPEL: Restez souverain. Abonnez-vous."
        else:
            if content_type == "technical":
                hook = f"TECH_INSIGHT: Audit completed on {text[:40]}."
                body = "ANALYSIS: Sentinel detected a Value Topology shift. Corrective measures active."
                cta = "STATUS: 70% Technical Alpha. Follow for audits."
            else:
                hook = f"CEO_UPDATE: Evaluating {text[:40]} engagement."
                body = "STRATEGY: Brand alignment confirmed. ROI exceeds threshold for Builder Status."
                cta = "ENAGAGEMENT: Community growth prioritized. 30% Social Reach."
        
        return f"{hook}\n{body}\n{cta}"

    def queue_for_approval(self, source, script, content_type):
        queue = []
        if os.path.exists(QUEUED_CONTENT):
            try:
                with open(QUEUED_CONTENT, "r") as f:
                    queue = json.load(f)
            except:
                queue = []
        
        queue.append({
            "source": source,
            "script": script,
            "type": content_type,
            "status": "pending_approval",
            "detected_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        with open(QUEUED_CONTENT, "w") as f:
            json.dump(queue, f, indent=2)
        print(f"[+] {content_type.upper()} script queued for Architect approval.")

if __name__ == "__main__":
    if not os.path.exists(KNOWLEDGE_BASE):
        os.makedirs(KNOWLEDGE_BASE)
        
    event_handler = InfluencerHandler()
    observer = Observer()
    observer.schedule(event_handler, KNOWLEDGE_BASE, recursive=False)
    observer.start()
    
    print(f"[*] AI Influencer Orchestrator started on {KNOWLEDGE_BASE}...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
