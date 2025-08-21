from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.clock import Clock
from kivy.uix.screenmanager import ScreenManager, Screen
from jnius import autoclass, PythonJavaClass, java_method
import requests

# ------------------------------
# CONFIG
# ------------------------------
API_KEY = "sk-your-deepseek-api-key-here"
MODEL = "deepseek/deepseek-r1-0528:free"
SAFE_WORDS = ["stop", "quit", "exit"]

PythonActivity = autoclass("org.kivy.android.PythonActivity")
TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
RecognizerIntent = autoclass("android.speech.RecognizerIntent")
Locale = autoclass("java.util.Locale")

# ------------------------------
# Speech Listener
# ------------------------------
class Listener(PythonJavaClass):
    __javainterfaces__ = ['android/speech/RecognitionListener']
    __javacontext__ = 'app'

    def __init__(self):
        super().__init__()
        self.last_result = ""

    @java_method('(Ljava/util/ArrayList;)V')
    def onResults(self, results):
        if results:
            self.last_result = results.get(0)

    @java_method('(I)V')
    def onError(self, error):
        print(f"[Speech Error] {error}")

    # no-ops
    @java_method('(I)V')
    def onReadyForSpeech(self, params): pass
    @java_method('([Ljava/lang/String;)V')
    def onPartialResults(self, partial): pass
    @java_method('()V')
    def onBeginningOfSpeech(self): pass
    @java_method('()V')
    def onEndOfSpeech(self): pass
    @java_method('(F)V')
    def onRmsChanged(self, rms): pass
    @java_method('(I)V')
    def onBufferReceived(self, buffer): pass
    @java_method('(I)V')
    def onEvent(self, event): pass

# ------------------------------
# TTS
# ------------------------------
tts = TextToSpeech(PythonActivity.mActivity, None)

def speak(text):
    tts.speak(text, TextToSpeech.QUEUE_FLUSH, None, None)
    print(f"[SPEAK]: {text}")

# ------------------------------
# AI Query
# ------------------------------
def query_deepseek(prompt, scenario=None):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "user", "content": prompt}]
    if scenario:
        messages.insert(0, {"role": "system",
                            "content": f"You are role-playing this prank: {scenario}. "
                                       f"If answers are unclear, ask clarifying questions."})

    data = {"model": MODEL, "messages": messages}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=20)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error contacting AI: {e}"

# ------------------------------
# SCREENS
# ------------------------------
class ScenarioScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation="vertical")
        self.scenario_input = TextInput(hint_text="Write prank scenario here...", size_hint_y=0.7)
        self.analyze_button = Button(text="Analyze Scenario", size_hint_y=0.3, on_press=self.analyze_scenario)
        self.status = Label(text="")
        layout.add_widget(self.scenario_input)
        layout.add_widget(self.analyze_button)
        layout.add_widget(self.status)
        self.add_widget(layout)

    def analyze_scenario(self, instance):
        text = self.scenario_input.text.strip()
        if not text:
            self.status.text = "Please enter prank details first!"
            return
        feedback = query_deepseek(f"Analyze this prank idea: {text}. "
                                  f"Say if it is clear enough, or suggest improvements.")
        self.status.text = feedback
        if "good" in feedback.lower() or "ready" in feedback.lower():
            self.manager.current = "start"

class StartScreen(Screen):
    def __init__(self, scenario, **kwargs):
        super().__init__(**kwargs)
        self.scenario = scenario
        layout = BoxLayout(orientation="vertical")
        self.label = Label(text="Scenario analyzed. Ready to start prank.")
        self.start_button = Button(text="Start Prank", on_press=self.start_prank)
        layout.add_widget(self.label)
        layout.add_widget(self.start_button)
        self.add_widget(layout)

    def start_prank(self, instance):
        speak("Hello! This is a prank call. Let's begin.")
        Clock.schedule_once(lambda dt: self.listen_loop(), 2)

    def listen_loop(self):
        listener = Listener()
        recognizer = SpeechRecognizer.createSpeechRecognizer(PythonActivity.mActivity)
        recognizer.setRecognitionListener(listener)
        intent = RecognizerIntent.getVoiceDetailsIntent(PythonActivity.mActivity)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
        recognizer.startListening(intent)

        def check_result(dt):
            if listener.last_result:
                user_input = listener.last_result.lower()
                if any(word in user_input for word in SAFE_WORDS):
                    speak("Safe word detected. Ending prank.")
                    return False
                response = query_deepseek(user_input, self.scenario)
                speak(response)
                listener.last_result = ""
                recognizer.startListening(intent)

        Clock.schedule_interval(check_result, 0.5)

# ------------------------------
# APP
# ------------------------------
class PhantomCallerApp(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(ScenarioScreen(name="scenario"))
        sm.add_widget(StartScreen(scenario="", name="start"))
        return sm

# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    PhantomCallerApp().run()    @java_method('(I)V')
    def onError(self, error):
        print(f"[Speech Error] {error}")

    # No-op methods
    @java_method('(I)V')
    def onReadyForSpeech(self, params): pass
    @java_method('([Ljava/lang/String;)V')
    def onPartialResults(self, partial): pass
    @java_method('()V')
    def onBeginningOfSpeech(self): pass
    @java_method('()V')
    def onEndOfSpeech(self): pass
    @java_method('(F)V')
    def onRmsChanged(self, rms): pass
    @java_method('(I)V')
    def onBufferReceived(self, buffer): pass
    @java_method('(I)V')
    def onEvent(self, event): pass

# ------------------------------
# TTS
# ------------------------------
tts = TextToSpeech(PythonActivity.mActivity, None)

def speak(text):
    tts.speak(text, TextToSpeech.QUEUE_FLUSH, None, None)
    print(f"[SPEAK]: {text}")

# ------------------------------
# AI Query
# ------------------------------
def query_deepseek(prompt):
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {"model": MODEL, "messages":[{"role":"user","content":prompt}]}
    try:
        r = requests.post(url, headers=headers, json=data, timeout=20)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error contacting AI: {e}"

# ------------------------------
# Kivy App
# ------------------------------
class PhantomCallerApp(App):
    def build(self):
        self.label = Label(text="Initializing Phantom Caller...")
        Clock.schedule_once(lambda dt: self.start_prank(), 1)
        return self.label

    def start_prank(self):
        speak(INTRO)
        self.listen_loop()

    def listen_loop(self):
        listener = Listener()
        recognizer = SpeechRecognizer.createSpeechRecognizer(PythonActivity.mActivity)
        recognizer.setRecognitionListener(listener)
        intent = RecognizerIntent.getVoiceDetailsIntent(PythonActivity.mActivity)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
        intent.putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())

        recognizer.startListening(intent)

        # Check result every 0.5s
        def check_result(dt):
            if listener.last_result:
                user_input = listener.last_result.lower()
                if any(word in user_input for word in SAFE_WORDS):
                    speak("Safe word detected. Ending the call.")
                    return
                response = query_deepseek(user_input)
                speak(response)
                listener.last_result = ""
                recognizer.startListening(intent)

        Clock.schedule_interval(check_result, 0.5)

# ------------------------------
# RUN
# ------------------------------
if __name__ == "__main__":
    PhantomCallerApp().run()
