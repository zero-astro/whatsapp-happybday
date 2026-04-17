#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp HappyBDay - Score-based script for detecting birthdays and congratulations.
"""

import subprocess
import re
import random
import os
import json
from datetime import datetime, timedelta
import sys

# Try to import dotenv from various locations
dotenv_found = False
try:
    from dotenv import load_dotenv
    dotenv_found = True
except ImportError:
    # Try user site-packages paths
    user_site = '/Users/kamaraka/Library/Python/3.9/lib/python/site-packages'
    
    if os.path.exists(user_site):
        sys.path.insert(0, user_site)
        try:
            from dotenv import load_dotenv
            dotenv_found = True
        except ImportError:
            pass

if not dotenv_found:
    print("ERROR: python-dotenv not found")
    sys.exit(1)

# Ensure we're using the right Python path
if sys.executable == '/opt/homebrew/bin/python3':
    # Try to find the correct python-dotenv installation
    import subprocess
    result = subprocess.run(['which', 'python3'], capture_output=True, text=True)
    if result.returncode == 0:
        python_path = result.stdout.strip()
        print(f"Using Python: {python_path}")

# --- Main Configuration ---
# Skip list format: comma-separated "Name|MM-DD" entries (e.g., "John|01-15,Jane|12-25")
# If only name is provided (no |), it's treated as a permanent skip
SKIP_LIST_RAW = os.environ.get("BIRTHDAY_SKIP_LIST", "")
def parse_skip_list(raw_string):
    """
    Parse skip list into two structures:
    - permanent_skips: set of lowercase names to always skip
    - birthday_skips: dict mapping (name_lower, mm-dd) -> True for date-based skips
    """
    permanent_skips = set()
    birthday_skips = {}
    
    if not raw_string.strip():
        return permanent_skips, birthday_skips
    
    entries = [entry.strip() for entry in raw_string.split(",")]
    for entry in entries:
        if "|" in entry:
            name, date = entry.split("|", 1)
            name = name.strip().lower()
            date = date.strip()
            birthday_skips[(name, date)] = True
        else:
            permanent_skips.add(entry.strip().lower())
    
    return permanent_skips, birthday_skips

SKIP_LIST_PERMANENT, SKIP_LIST_BIRTHDAY = parse_skip_list(SKIP_LIST_RAW)

# Scoring system and parameters from environment variables
MIN_MESSAGES = int(os.environ.get("BIRTHDAY_MIN_MESSAGES", "3"))
CONFIDENCE_THRESHOLD = int(os.environ.get("BIRTHDAY_CONFIDENCE_THRESHOLD", "120"))

# File locations
SKILL_DIR = os.path.expanduser("~/.openclaw/skills/whatsapp-happybday")
DATA_DIR = os.path.join(SKILL_DIR, "data")
MESSAGES_FILE = os.path.join(SKILL_DIR, "messages.json")
SCORING_WORDS_FILE = os.path.join(SKILL_DIR, "scoring_words.json")
STATE_FILE = os.path.join(DATA_DIR, "name_counter.json")
# --- End Configuration ---

# Birthday-related keywords to detect congratulatory messages from the human
CONGRATS_KEYWORDS = [
    "zorionak", "happy birthday", "happybday", "urte on", "urte asko",
    "congratulations", "congrats", "best wishes", "feliz cumplea\u00f1os",
    "onngia", "pasa eguna", "ospatu"
]

# Stopwords: capitalized words that are NOT names (reduce false positives)
# Loaded from BIRTHDAY_STOPWORDS env var (comma-separated, case-insensitive)
# Default English stopwords if not set
_DEFAULT_STOPWORDS = [
    # Common English articles & conjunctions
    "the", "and", "for", "are", "but", "not", "you", "all",
    "can", "had", "her", "was", "one", "our", "out", "has",
    "have", "been", "from", "this", "that", "with", "will",
    "each", "about", "which", "when", "than", "them", "some",
    "would", "their", "there", "what", "these", "other",
    # Birthday-related (not names)
    "happy", "birthday", "celebrate", "wishes", "today",
    # Greeting patterns
    "good", "morning", "afternoon", "evening", "night",
]

def _load_stopwords():
    """
    Load stopwords from BIRTHDAY_STOPWORDS env var.
    Expected format: comma-separated words, e.g. "the,and,for,happy,birthday"
    Falls back to defaults if not set or empty.
    Returns a set of lowercase strings.
    """
    raw = os.environ.get("BIRTHDAY_STOPWORDS", "").strip()
    if not raw:
        return set(w.lower() for w in _DEFAULT_STOPWORDS)
    return set(w.strip().lower() for w in raw.split(",") if w.strip())

STOPWORDS = _load_stopwords()

def load_messages():
    """Load congratulatory messages from JSON file"""
    try:
        with open(MESSAGES_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {"greetings": ["Happy birthday, {name}!"], "wishes": ["Have a great day!"], "emojis": ["🎉"]}

def load_scoring_words():
    """Load scoring words from JSON file or use defaults"""
    try:
        with open(SCORING_WORDS_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {
            "birthday": {"words": ["birthday", "years", "candle", "cake"], "points": 40},
            "general": {"words": ["congratulations", "congrats", "celebrate", "day", "happy", "party"], "points": 15},
            "negative": {"words": ["family", "son", "daughter", "child", "kid", "cute", "work", "job"], "points": -50}
        }

def run_wacli_command(cmd):
    """Execute wacli command"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60)
        return result.stdout, result.stderr, result.returncode
    except Exception as e:
        return "", str(e), 1

def get_groups():
    """Get list of WhatsApp group JIDs"""
    stdout, stderr, rc = run_wacli_command("wacli chats list --json")
    if rc != 0 or not stdout.strip():
        return []

    try:
        response = json.loads(stdout)
        chats = response.get("data")
        if not chats:
            return []

        jid_list = [
            chat["JID"] 
            for chat in chats 
            if chat.get("Kind") == "group" and "JID" in chat
        ]
        return jid_list
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error processing data: {e}")
        return []

def get_recent_messages(group_jid, today):
    """Get recent messages from a group (Text fields only)"""
    cmd = f'wacli messages list --chat "{group_jid}" --after {today} --json'
    stdout, stderr, rc = run_wacli_command(cmd)
    
    if rc != 0 or not stdout.strip():
        return []

    try:
        response = json.loads(stdout)
        data_block = response.get("data", {})
        messages_list = data_block.get("messages", [])
        
        if not messages_list:
            return []

        texts = [
            msg["Text"] 
            for msg in messages_list 
            if msg.get("Text") and msg["Text"].strip()
        ]
        return texts
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        print(f"Error processing messages: {e}")
        return []

def load_state():
    """Load state file"""
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f: return json.load(f)
    return {}

def save_state(state):
    """Save state file"""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STATE_FILE, 'w') as f: json.dump(state, f, indent=2)   

def detect_names_with_nlp(text):
    """
    Extract candidate names from text using regex.
    Filters out stopwords and scoring blacklist words.
    Returns list of capitalized proper noun candidates.
    """
    scoring_words = load_scoring_words()
    blacklist = set()
    for category in scoring_words.values():
        for word in category["words"]:
            blacklist.add(word.lower())

    # Find all capitalized words with 3+ letters (likely proper nouns)
    candidates = re.findall(r'\b[A-Z][a-z]{2,}\b', text)
    
    # Filter out stopwords and blacklist words
    names = [
        name for name in candidates
        if name.lower() not in STOPWORDS
        and name.lower() not in blacklist
    ]
    return names

def get_today_month_day():
    """Get today's month-day as MM-DD"""
    return datetime.now().strftime("%m-%d")

def check_user_already_congratulated(name):
    """
    Check if the human (FromMe=true) already sent a congratulatory message to this person today.
    Searches across ALL groups, not just the current one.
    Returns True if found, False otherwise.
    """
    today = get_today_key()
    all_groups = get_groups()  # Get all active groups
    name_lower = name.lower()
    
    for g_jid in all_groups:
        cmd = f'wacli messages list --chat "{g_jid}" --after {today} --json'
        stdout, stderr, rc = run_wacli_command(cmd)
        
        if rc != 0 or not stdout.strip():
            continue
        
        try:
            response = json.loads(stdout)
            data_block = response.get("data", {})
            messages_list = data_block.get("messages", [])
            
            for msg in messages_list:
                # Only check messages sent by the human (FromMe=true)
                if not msg.get("FromMe"):
                    continue
                
                text = msg.get("Text", "").lower()
                
                # Check if the message contains the person's name AND a congratulatory keyword
                has_name = name_lower in text
                has_congrats = any(kw.lower() in text for kw in CONGRATS_KEYWORDS)
                
                if has_name and has_congrats:
                    print(f"   ⚠️  Human already congratulated {name} today")
                    return True
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            print(f"   ⚠️  Error checking user messages: {e}")
    
    return False

def is_in_skip_list(name):
    """
    Check if name is in the skip list.
    Returns:
        - True if permanently skipped
        - False if not in skip list at all
        - 'date_based' if only skipped on specific dates (caller must check date)
    """
    name_lower = name.lower()
    
    # Check permanent skips first
    if name_lower in SKIP_LIST_PERMANENT:
        return True
    
    # Check birthday-based skips
    today_md = get_today_month_day()
    for (skip_name, skip_date) in SKIP_LIST_BIRTHDAY.keys():
        if skip_name == name_lower:
            # Name is in birthday_skips - check if it's today
            if skip_date == today_md:
                return True
            else:
                # Different date - not skipped today
                return False
    
    # Not in any skip list
    return False

def select_random_message(name):
    """Select a random congratulatory message by combining parts"""
    messages_data = load_messages()
    greeting = random.choice(messages_data["greetings"])
    wish = random.choice(messages_data["wishes"])
    emoji_list = messages_data["emojis"]
    emojis = "".join(random.choices(emoji_list, k=random.randint(1, 4))) if emoji_list else ""
    return f"{greeting.format(name=name)} {wish} {emojis}"

def calculate_message_score(text):
    """Calculate the score of a message"""
    scoring_words = load_scoring_words()
    score = 0
    text_lower = text.lower()
    for category in scoring_words.values():
        for word in category["words"]:
            if word in text_lower:
                score += category["points"]
    return score

def get_today_key():
    """Get today's date as a key"""
    return datetime.now().strftime("%Y-%m-%d")

def send_message(group_jid, msg):
    cmd = f'wacli send text --message "{msg}" --to "{group_jid}"'
    stdout, stderr, rc = run_wacli_command(cmd)
    if rc != 0 or not stdout.strip():
        return False
    return True

def process_group(group_jid, state):
    """Process a group using the new scoring system."""
    print(f"\n📱 Group: {group_jid}")
    today = get_today_key()
    if today not in state: state[today] = {}
    
    messages = get_recent_messages(group_jid, today)
    if not messages: return state

    processed_key, sent_key = f"{today}_processed", f"{today}_sent"
    processed_today = state.get(processed_key, [])
    sent_today = state.get(sent_key, [])

    for message in messages:
        if message in processed_today: continue
        processed_today.append(message)
        
        score = calculate_message_score(message)
        if score <= 0: continue
            
        names = detect_names_with_nlp(message)
        for name in names:
            if is_in_skip_list(name) or name in sent_today: continue
            
            if name not in state[today]: state[today][name] = {"count": 0, "score": 0}
            
            state[today][name]["count"] += 1
            state[today][name]["score"] += score
            
            count, current_score = state[today][name]["count"], state[today][name]["score"]
            print(f"   👤 {name}: message #{count} | Score: +{score} -> {current_score}")
            
            if count >= MIN_MESSAGES and current_score >= CONFIDENCE_THRESHOLD:
                print(f"   🎉 Congratulating {name}... ({count} messages, {current_score} points)")
                
                # Check if the human already congratulated this person today
                user_already_sent = check_user_already_congratulated(name)
                
                if user_already_sent:
                    print(f"   ⏭️  Skipping {name} - Human already sent a message")
                    # Mark as sent to prevent duplicate bot messages
                    sent_today.append(name)
                    continue
                
                msg = select_random_message(name)
                
                if os.environ.get("BIRTHDAY_SIMULATE", "true").lower() == "true":
                    print(f"   ✅ SIMULATION: '{msg}' would be sent")
                    sent_flag = True
                else:
                    sent_flag = send_message(group_jid, msg)

                if sent_flag:
                    sent_today.append(name)
                    print(f"   ✅ SENT: '{msg}' was sent")
    
    state[processed_key], state[sent_key] = processed_today, sent_today
    return state

def main():
    """Main function"""
    print("="*60 + "\n🎉 WhatsApp HappyBDay - Score-Based Monitor\n" + "="*60)
    
    load_dotenv()
    state = load_state()
    
    groups = get_groups()
    if not groups:
        print("❌ No groups found")
        return

    for group in groups:
        state = process_group(group, state)
    
    # Clean up states older than 7 days
    cutoff_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    for k in list(state.keys()):
        if not k.startswith(str(datetime.now().year)) or k < cutoff_date:
            del state[k]
    
    save_state(state)
    print("\n✅ Process finished.\n" + "="*60)

if __name__ == "__main__":
    main()
