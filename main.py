# main.py
# J.A.R.V.I.S.-style prank with extremely realistic free streaming TTS (Coqui) and AI responses

import os
import threading
import requests
import tempfile
import random
import time

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.core.audio import SoundLoader

# ---- Android / Java bridges (guarded for desktop) ----
try:
    from jnius import autoclass, PythonJavaClass, java_method

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
    RecognizerIntent = autoclass("android.speech.RecognizerIntent")
    Intent = autoclass("android.content.Intent")
    Bundle = autoclass("android.os.Bundle")
    Locale = autoclass("java.util.Locale")

    try:
        from android.permissions import request_permissions, Permission
        request_permissions([Permission.RECORD_AUDIO])
    except Exception:
        pass

    ANDROID = True
except Exception:
    ANDROID = False
    PythonActivity = None
    SpeechRecognizer = None
    RecognizerIntent = None
    Intent = None
    Bundle = None
    Locale = None

# ------------------------------
# CONFIG
# ------------------------------
API_KEY = os.getenv("OPENROUTER_API_KEY") or "REPLACE_ME"
MODEL = "deepseek/deepseek-r1-0528:free"
SAFE_WORDS = {"stop", "quit", "exit", "cancel", "enough"}
INTRO = "This is a consented demo with voice interaction. Let us begin."
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ------------------------------
# Coqui TTS (extremely realistic)
# ------------------------------
try:
    from TTS.api import TTS
    tts = TTS(model_name="tts_models/en/vctk/vits", progress_bar=False)
    COQUI_READY = True
except Exception:
    COQUI_READY = False
    print("[WARN] Coqui TTS not available. Audio will fallback to print.")

FILLERS = ["Hmm…", "Ah…", "Let’s see…", "Okay…"]

def speak_realistic(text: str):
    """Speak text with fillers, pitch/speed variation, and chunked streaming."""
    # Random thinking delay
    time.sleep(random.uniform(0.3, 1.0))

    # Randomly prepend a filler
    if random.random() < 0.3:
        text = random.choice(FILLERS) + " " + text

    # Split text into chunks (~8 words per chunk)
    words = text.split()
    chunks = [" ".join(words[i:i+8]) for i in range(0, len(words), 8)]

    for chunk in chunks:
        if COQUI_READY:
            tmp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            tts.tts_to_file(text=chunk, file_path=tmp_file.name)
            sound = SoundLoader.load(tmp_file.name)
            if sound:
                sound.play()
        print(f"[SPEAK]: {chunk}")
        time.sleep(0.05)

# ------------------------------
# DeepSeek / OpenRouter
# ------------------------------
def query_deepseek(user_text: str, scenario: str | None = None) -> str:
    if not API_KEY or API_KEY == "REPLACE_ME":
        return "API key not configured. Please set OPENROUTER_API_KEY in your environment."

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are J.A.R.V.I.S., a calm, respectful assistant. "
                "This interaction is a **demo with consent**; keep replies brief, safe, and non-harmful."
            )
        }
    ]
    if scenario:
        messages.append({"role": "system", "content": f"Scenario context for role-play: {scenario}"})
    messages.append({"role": "user", "content": user_text})

    data = {"model": MODEL, "messages": messages}

    try:
        r = requests.post(OPENROUTER_URL, headers=headers, json=data, timeout=30)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error contacting AI: {e}"

# ------------------------------
# Android Speech Listener
# ------------------------------
if ANDROID:
    class Listener(PythonJavaClass):
        __javainterfaces__ = ['android/speech/RecognitionListener']
        __javacontext__ = 'app'

        def __init__(self):
            super().__init__()
            self.last_text = ""

        @java_method('(Landroid/os/Bundle;)V')
        def onResults(self, results):
            try:
                arr = results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                if arr and not arr.isEmpty():
                    self.last_text = arr.get(0)
            except Exception as e:
                print(f"[onResults error] {e}")

        @java_method('(Landroid/os/Bundle;)V') 
        def onPartialResults(self, partial): pass
        @java_method('(I)V') 
        def onError(self, error): print(f"[Speech Error] code={error}")
        @java_method('(Landroid/os/Bundle;)V') 
        def onReadyForSpeech(self, params): pass
        @java_method('()V') 
        def onBeginningOfSpeech(self): pass
        @java_method('()V') 
        def onEndOfSpeech(self): pass
        @java_method('([B)V') 
        def onBufferReceived(self, buffer): pass
        @java_method('(F)V') 
        def onRmsChanged(self, rms): pass
        @java_method('(ILandroid/os/Bundle;)V') 
        def onEvent(self, eventType, params): pass

# ------------------------------
# UI SCREENS
# ------------------------------
class ScenarioScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)

        self.scenario_input = TextInput(
            hint_text="Describe the scenario for your voice demo...",
            size_hint_y=0.6
        )
        self.status = Label(text="[i]Awaiting scenario…[/i]", markup=True, size_hint_y=0.2)
        btn_row = BoxLayout(size_hint_y=0.2, spacing=8)
        self.analyze_button = Button(text="Analyze Scenario")
        self.next_button = Button(text="Proceed", disabled=True)
        self.analyze_button.bind(on_press=self.analyze_scenario)
        self.next_button.bind(on_press=self.go_next)
        btn_row.add_widget(self.analyze_button)
        btn_row.add_widget(self.next_button)
        root.add_widget(self.scenario_input)
        root.add_widget(self.status)
        root.add_widget(btn_row)
        self.add_widget(root)

    def analyze_scenario(self, *_):
        text = self.scenario_input.text.strip()
        if not text:
            self.status.text = "[color=ff4444]Enter scenario first.[/color]"
            return

        self.status.text = "[i]Analyzing scenario…[/i]"
        self.next_button.disabled = True

        def work():
            feedback = query_deepseek(
                f"Analyze this scenario for a consented voice demo: {text}. "
                f"Is it clear and safe? Suggest one concise improvement if needed."
            )
            def update_ui(dt):
                self.status.text = feedback
                if any(k in feedback.lower() for k in ("clear", "safe", "ready", "good")):
                    self.next_button.disabled = False
            Clock.schedule_once(update_ui, 0)

        threading.Thread(target=work, daemon=True).start()

    def go_next(self, *_):
        app = App.get_running_app()
        app.scenario_text = self.scenario_input.text.strip()
        self.manager.current = "start"

class StartScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=12, spacing=8)
        self.info = Label(text="Ready. Press [b]Start Demo[/b].", markup=True, size_hint_y=0.2)
        self.live = Label(text="", size_hint_y=0.6)
        btn_row = BoxLayout(size_hint_y=0.2, spacing=8)
        self.start_btn = Button(text="Start Demo")
        self.stop_btn = Button(text="Stop", disabled=True)
        btn_row.add_widget(self.start_btn)
        btn_row.add_widget(self.stop_btn)
        root.add_widget(self.info)
        root.add_widget(self.live)
        root.add_widget(btn_row)
        self.add_widget(root)

        self.start_btn.bind(on_press=self.start_demo)
        self.stop_btn.bind(on_press=self.stop_demo)

        self.listener = None
        self.recognizer = None
        self.intent = None
        self._interval = None
        self._running = False

    def _setup_speech(self):
        if not ANDROID:
            self.info.text = "[color=ff4444]Desktop mode: STT not available[/color]"
            return False
        if not SpeechRecognizer.isRecognitionAvailable(PythonActivity.mActivity):
            self.info.text = "[color=ff4444]Speech recognition unavailable[/color]"
            return False
        self.listener = Listener()
        self.recognizer = SpeechRecognizer.createSpeechRecognizer(PythonActivity.mActivity)
        self.intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
        self.intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                             RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        self.intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
        self.intent.putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, True)
        self.recognizer.setRecognitionListener(self.listener)
        return True

    def start_demo(self, *_):
        app = App.get_running_app()
        scenario = getattr(app, "scenario_text", "")

        self.info.text = "Starting demo…"
        self.start_btn.disabled = True
        self.stop_btn.disabled = False
        self._running = True

        speak_realistic(INTRO)

        if not self._setup_speech():
            self.info.text = "[color=ff4444]Speech not available.[/color]"
            self.start_btn.disabled = False
            self.stop_btn.disabled = True
            return

        self.recognizer.startListening(self.intent)

        def poll(dt):
            if not self._running:
                return False
            heard = (self.listener.last_text or "").strip()
            if not heard:
                return
            self.live.text = f"[Heard] {heard}"
            self.listener.last_text = ""

            if any(w in heard.lower() for w in SAFE_WORDS):
                speak_realistic("Safe word detected. Ending the demo now.")
                self.stop_demo()
                return

            def work():
                reply = query_deepseek(heard, scenario=scenario)
                Clock.schedule_once(lambda dt: self._speak_and_display(reply), 0)

            threading.Thread(target=work, daemon=True).start()

            try:
                self.recognizer.startListening(self.intent)
            except Exception as e:
                print(f"[Recognizer restart error] {e}")

        self._interval = Clock.schedule_interval(poll, 0.5)

    def _speak_and_display(self, reply: str):
        self.live.text = f"{self.live.text}\n[J.A.R.V.I.S.] {reply}"
        speak_realistic(reply)

    def stop_demo(self, *_):
        self._running = False
        self.start_btn.disabled = False
        self.stop_btn.disabled = True
        self.info.text = "Demo stopped."
        try:
            if self._interval:
                self._interval.cancel()
                self._interval = None
            if ANDROID and self.recognizer:
                self.recognizer.cancel()
                self.recognizer.destroy()
        except Exception as e:
            print(f"[Stop error] {e}")

# ------------------------------
# APP
# ------------------------------
class PhantomCallerApp(App):
    title = "Voice Demo (J.A.R.V.I.S.)"

    def build(self):
        self.scenario_text = ""
        sm = ScreenManager(transition=FadeTransition())
        sm.add_widget(ScenarioScreen(name="scenario"))
        sm.add_widget(StartScreen(name="start"))
        return sm

# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    PhantomCallerApp().run()
