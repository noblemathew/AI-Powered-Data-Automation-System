"""
J.A.R.V.I.S. v3.0 — Just A Rather Very Intelligent System
Iron Man Edition — Built on your original college project
Enhanced with PC control, personality, and new commands.

Install dependencies:
    pip install pyttsx3 speechrecognition pyaudio requests beautifulsoup4
    pip install psutil pyautogui pillow wikipedia

Windows-only extras (optional):
    pip install pywin32

Usage:
    python jarvis_v3.py
"""

import webbrowser
import requests
from bs4 import BeautifulSoup
import speech_recognition as sr
import pyttsx3
import datetime
import random
import os
import sys
import time
import subprocess
import psutil            # pip install psutil
import pyautogui         # pip install pyautogui
import wikipedia         # pip install wikipedia

# ─────────────────────────────────────────────────────────────
#  ENGINE SETUP  ─ done once at startup for speed
# ─────────────────────────────────────────────────────────────

engine = pyttsx3.init()
try:
    import comtypes.client
    tts = comtypes.client.CreateObject("SAPI.SpVoice")
    voices_col = tts.GetVoices()
    # Pick first available voice
    for i in range(voices_col.Count):
        try:
            v = voices_col.Item(i)
            name = v.GetDescription()
            if 'david' in name.lower() or 'male' in name.lower():
                engine._driver._tts.Voice = v
                break
        except Exception:
            continue
except Exception as e:
    print(f"  [WARN] Could not set voice: {e}. Using default.")

engine.setProperty('rate', 165)
engine.setProperty('volume', 1.0)

r = sr.Recognizer()
r.energy_threshold = 3000
r.dynamic_energy_threshold = True


# ─────────────────────────────────────────────────────────────
#  PERSONALITY BANKS
# ─────────────────────────────────────────────────────────────

GREET_LINES = [
    "Welcome back, Sir. All systems are operational.",
    "Good to have you back, Sir. How can I assist?",
    "Ah, you're home. I've kept everything running smoothly.",
    "Sir! Daddy's home. The arc reactor missed you.",
    "Welcome back. I took the liberty of running diagnostics while you were gone.",
    "All systems online. Ready to serve, Sir.",
    "You know, most people knock. But welcome back regardless, Sir.",
]

INTRO_RESPONSES = [
    "I am J.A.R.V.I.S., Sir. Just A Rather Very Intelligent System.",
    "Your faithful assistant, at your service. Jarvis, Sir.",
    "The name's Jarvis. I believe you built me, so this is slightly awkward.",
    "I am Jarvis, Sir — your personal AI, butler, and occasional voice of reason.",
]

UNKNOWN_RESPONSES = [
    "I'm not sure I understood that, Sir. Could you repeat it?",
    "Pardon, Sir? The audio was unclear.",
    "I didn't catch that. Try again?",
    "My apologies — could you rephrase that, Sir?",
]

FAREWELL_LINES = [
    "Goodbye, Sir. I'll keep the lights on.",
    "Signing off. The mansion is in good hands.",
    "Farewell, Sir. J.A.R.V.I.S. powering down.",
    "Until next time, Sir. Stay out of trouble.",
]


# ─────────────────────────────────────────────────────────────
#  CORE SPEAK FUNCTION
# ─────────────────────────────────────────────────────────────

def speak(text: str) -> None:
    """Speak text aloud and also print it to the terminal."""
    print(f"\n  [JARVIS] {text}\n")
    engine.say(text)
    engine.runAndWait()


# ─────────────────────────────────────────────────────────────
#  INTRO SEQUENCE  ─ "Daddy's home"
# ─────────────────────────────────────────────────────────────

def boot_sequence() -> None:
    """Play the Iron Man style boot-up intro."""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=" * 60)
    print("   J.A.R.V.I.S.  v3.0  —  STARK INDUSTRIES")
    print("   Just A Rather Very Intelligent System")
    print("=" * 60)
    lines = [
        "  > Initializing core systems...",
        "  > Loading speech recognition engine...",
        "  > Connecting to neural inference module...",
        "  > Running system diagnostics...",
        "  > Arc reactor: STABLE",
        "  > All systems nominal.",
        "",
        "  >>> JARVIS ONLINE <<<",
        "",
    ]
    for line in lines:
        print(line)
        time.sleep(0.25)

    speak(random.choice(GREET_LINES))


# ─────────────────────────────────────────────────────────────
#  LISTENING HELPER
# ─────────────────────────────────────────────────────────────

def listen(prompt: str = "Listening...") -> str:
    """
    Listen for one voice command.
    Returns the recognised text in lower-case, or '' on failure.
    """
    print(f"  [{prompt}]")
    try:
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.4)
            audio = r.listen(source, timeout=8, phrase_time_limit=6)
        text = r.recognize_google(audio)
        print(f"  [YOU] {text}")
        return text.lower()
    except sr.WaitTimeoutError:
        return ''
    except sr.UnknownValueError:
        return ''
    except Exception as e:
        print(f"  [ERROR] {e}")
        return ''


# ─────────────────────────────────────────────────────────────
#  FEATURE FUNCTIONS
# ─────────────────────────────────────────────────────────────

def web_search() -> None:
    speak("What would you like me to search for, Sir?")
    query = listen("Speak your search query")
    if query:
        speak(f"Searching for {query} now, Sir.")
        webbrowser.open_new_tab(f"https://www.google.com/search?q={query}")
    else:
        speak("I didn't catch that. Try again, Sir.")


def youtube_search() -> None:
    speak("What would you like to watch on YouTube, Sir?")
    query = listen("Speak your YouTube query")
    if query:
        speak(f"Opening YouTube for {query}.")
        webbrowser.open_new_tab(f"https://www.youtube.com/results?search_query={query}")


def read_news() -> None:
    speak("Fetching the latest headlines from BBC News, Sir.")
    try:
        url = 'https://www.bbc.com/news'
        soup = BeautifulSoup(requests.get(url, timeout=5).text, 'html.parser')
        headlines = soup.find('body').find_all('h3')
        count = 0
        for h in headlines:
            text = h.text.strip()
            if text and len(text) > 10:
                print(f"  • {text}")
                speak(text)
                count += 1
                if count >= 5:
                    break
        if count == 0:
            speak("I couldn't retrieve headlines at the moment, Sir.")
    except Exception:
        speak("News feed unavailable, Sir. Check your connection.")


def date_and_time() -> None:
    now = datetime.datetime.now()
    date_str = now.strftime("%A, %B %d, %Y")
    time_str = now.strftime("%I:%M %p")
    speak(f"The current date is {date_str}, and the time is {time_str}, Sir.")


def wikipedia_search() -> None:
    speak("What topic shall I look up on Wikipedia, Sir?")
    query = listen("Speak your topic")
    if query:
        try:
            speak(f"Looking up {query}, Sir.")
            result = wikipedia.summary(query, sentences=3)
            speak(result)
        except wikipedia.exceptions.DisambiguationError:
            speak("That topic is ambiguous, Sir. Could you be more specific?")
        except wikipedia.exceptions.PageError:
            speak("I couldn't find a Wikipedia article on that, Sir.")


def system_info() -> None:
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    speak(f"System report, Sir. CPU usage is {cpu:.0f} percent. "
          f"Memory is at {mem:.0f} percent. "
          f"Disk usage is {disk:.0f} percent.")


def take_screenshot() -> None:
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.expanduser(f"~/Desktop/JARVIS_screenshot_{ts}.png")
    try:
        img = pyautogui.screenshot()
        img.save(path)
        speak(f"Screenshot captured and saved to your Desktop, Sir.")
    except Exception as e:
        speak("I was unable to take a screenshot, Sir.")
        print(f"  [ERROR] {e}")


def open_application(name: str) -> None:
    """Open common Windows / cross-platform apps by keyword."""
    apps = {
        'notepad':    'notepad.exe',
        'calculator': 'calc.exe',
        'paint':      'mspaint.exe',
        'explorer':   'explorer.exe',
        'task manager': 'taskmgr.exe',
        'chrome':     'chrome',
        'firefox':    'firefox',
        'vlc':        'vlc',
        'word':       'winword',
        'excel':      'excel',
    }
    for key, cmd in apps.items():
        if key in name:
            speak(f"Opening {key.title()}, Sir.")
            try:
                subprocess.Popen(cmd, shell=True)
            except Exception:
                speak(f"I couldn't open {key.title()}. Make sure it's installed, Sir.")
            return
    speak(f"I don't know how to open that application, Sir.")


def volume_control(direction: str) -> None:
    if 'up' in direction or 'increase' in direction:
        for _ in range(5):
            pyautogui.press('volumeup')
        speak("Volume increased, Sir.")
    elif 'down' in direction or 'decrease' in direction or 'lower' in direction:
        for _ in range(5):
            pyautogui.press('volumedown')
        speak("Volume decreased, Sir.")
    elif 'mute' in direction:
        pyautogui.press('volumemute')
        speak("Audio muted, Sir.")


def shutdown_pc() -> None:
    speak("Are you sure you want to shut down, Sir? Say yes to confirm.")
    confirm = listen("Confirm shutdown")
    if 'yes' in confirm:
        speak("Shutting down the system. Goodbye, Sir.")
        os.system('shutdown /s /t 5' if os.name == 'nt' else 'shutdown -h now')
    else:
        speak("Shutdown cancelled, Sir.")


def restart_pc() -> None:
    speak("Confirm restart, Sir. Say yes to proceed.")
    confirm = listen("Confirm restart")
    if 'yes' in confirm:
        speak("Restarting now, Sir.")
        os.system('shutdown /r /t 5' if os.name == 'nt' else 'reboot')
    else:
        speak("Restart cancelled.")


def lock_pc() -> None:
    speak("Locking the workstation, Sir.")
    if os.name == 'nt':
        subprocess.call('rundll32 user32.dll,LockWorkStation')
    else:
        subprocess.call(['gnome-screensaver-command', '--lock'])


def tell_joke() -> None:
    jokes = [
        "Why don't scientists trust atoms? Because they make up everything.",
        "I tried to make a chemistry joke but I knew I would get no reaction.",
        "Why did the scarecrow win an award? Because he was outstanding in his field.",
        "I'm reading a book about anti-gravity. It's impossible to put down.",
        "Sir, I have an infinite number of jokes, but I'll spare you for now.",
    ]
    speak(random.choice(jokes))


def weather_check() -> None:
    speak("Which city should I check the weather for, Sir?")
    city = listen("Speak city name")
    if city:
        webbrowser.open_new_tab(f"https://www.google.com/search?q=weather+in+{city}")
        speak(f"Opening weather report for {city}, Sir.")


def help_menu() -> None:
    commands = [
        "search — web search",
        "youtube — YouTube search",
        "news — read BBC headlines",
        "time or date — current time and date",
        "wikipedia — look up a topic",
        "system — system performance report",
        "screenshot — capture the screen",
        "open notepad, calculator, chrome, etc.",
        "volume up, volume down, mute",
        "weather — check weather",
        "joke — hear a joke",
        "lock — lock the screen",
        "shutdown or restart the PC",
        "goodbye or exit — close Jarvis",
    ]
    speak("Here are the available commands, Sir.")
    for cmd in commands:
        print(f"   • {cmd}")


# ─────────────────────────────────────────────────────────────
#  COMMAND ROUTER
# ─────────────────────────────────────────────────────────────

def process_command(cmd: str) -> bool:
    """
    Route a recognised voice command.
    Returns False if Jarvis should exit, True to keep listening.
    """
    if not cmd:
        return True

    # Exit
    if any(w in cmd for w in ['goodbye', 'bye', 'exit', 'quit', 'shut yourself down']):
        speak(random.choice(FAREWELL_LINES))
        return False

    # Identity / greeting
    if any(w in cmd for w in ['who are you', 'your name', 'what are you']):
        speak(random.choice(INTRO_RESPONSES))

    elif any(w in cmd for w in ['hello', 'hi jarvis', 'hey jarvis', 'wake up', 'daddy', 'home']):
        speak(random.choice(GREET_LINES))

    # Web
    elif 'search' in cmd and 'youtube' not in cmd:
        web_search()

    elif 'youtube' in cmd:
        youtube_search()

    elif 'weather' in cmd:
        weather_check()

    elif 'wikipedia' in cmd or 'wiki' in cmd:
        wikipedia_search()

    # Information
    elif 'news' in cmd or 'headline' in cmd:
        read_news()

    elif 'time' in cmd or 'date' in cmd or 'day' in cmd:
        date_and_time()

    elif 'system' in cmd or 'cpu' in cmd or 'memory' in cmd or 'performance' in cmd:
        system_info()

    # PC control
    elif 'screenshot' in cmd or 'screen capture' in cmd:
        take_screenshot()

    elif 'volume' in cmd or 'mute' in cmd:
        volume_control(cmd)

    elif 'open' in cmd or 'launch' in cmd or 'start' in cmd:
        open_application(cmd)

    elif 'lock' in cmd and 'screen' in cmd or cmd == 'lock':
        lock_pc()

    elif 'shutdown' in cmd or 'shut down' in cmd or 'power off' in cmd:
        shutdown_pc()

    elif 'restart' in cmd or 'reboot' in cmd:
        restart_pc()

    # Fun
    elif 'joke' in cmd or 'funny' in cmd:
        tell_joke()

    # Help
    elif 'help' in cmd or 'commands' in cmd or 'what can you do' in cmd:
        help_menu()

    else:
        speak(random.choice(UNKNOWN_RESPONSES))

    return True


# ─────────────────────────────────────────────────────────────
#  MAIN LOOP
# ─────────────────────────────────────────────────────────────

def main() -> None:
    boot_sequence()

    print("\n  Type Ctrl+C to exit. Speak a command to begin.\n")
    print("  TIP: Say 'help' for a list of commands.\n")

    while True:
        try:
            command = listen("Awaiting command")
            if command:
                keep_going = process_command(command)
                if not keep_going:
                    break
        except KeyboardInterrupt:
            speak("Keyboard interrupt detected. Signing off, Sir.")
            break
        except Exception as e:
            print(f"  [LOOP ERROR] {e}")
            time.sleep(1)


if __name__ == '__main__':
    main()