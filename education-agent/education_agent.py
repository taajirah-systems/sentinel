import yaml
import os
import datetime

LESSONS_PATH = "/Users/taajirah_systems/sentinel/education-agent/curriculum/lessons.yaml"
LOGS_DIR = "/Users/taajirah_systems/.openclaw/workspace/child_logs/"

def send_daily_lesson():
    if not os.path.exists(LESSONS_PATH):
        print("[-] Error: Curriculum not found.")
        return

    with open(LESSONS_PATH, "r") as f:
        curriculum = yaml.safe_load(f)

    # Simple logic: pick lesson based on the day of the week or a counter
    # For now, we'll just simulate Day 1
    lesson = curriculum['lessons'][0]
    
    print(f"[*] Dispatching Lesson: {lesson['title']}")
    message = f"{lesson['content']}\n\nPROMPT: {lesson['prompt']}"
    
    # Simulate WhatsApp Send
    simulate_whatsapp_send(message)
    
    # Log the interaction locally (Privacy-first)
    log_interaction(lesson, "sent")

def simulate_whatsapp_send(message):
    print("------------------------------------------")
    print(f"WHATSAPP MESSAGE SENT:")
    print(message)
    print("------------------------------------------")

def log_interaction(lesson, status):
    if not os.path.exists(LOGS_DIR):
        os.makedirs(LOGS_DIR)
        
    log_file = os.path.join(LOGS_DIR, f"lesson_{datetime.date.today()}.txt")
    with open(log_file, "a") as f:
        f.write(f"[{datetime.datetime.now()}] STATUS: {status}\n")
        f.write(f"LESSON: {lesson['title']}\n")
        f.write("-" * 20 + "\n")

if __name__ == "__main__":
    send_daily_lesson()
