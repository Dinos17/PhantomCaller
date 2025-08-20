from kivy.app import App
from kivy.uix.label import Label
from kivy.clock import Clock
from jnius import autoclass, PythonJavaClass, java_method
import requests

# ------------------------------
# CONFIG
# ------------------------------
API_KEY = "sk-your-deepseek-api-key-here"
MODEL = "deepseek/deepseek-r1-0528:free"
SAFE_WORDS = ["stop", "quit", "exit"]
INTRO = "Hello! This is a fictional special offers department. Say 'yes' if you consent to continue."

# ------------------------------
# Android TTS & Speech
# ------------------------------
PythonActivity = autoclass("org.kivy.android.PythonActivity")
TextToSpeech = autoclass("android.speech.tts.TextToSpeech")
SpeechRecognizer = autoclass("android.speech.SpeechRecognizer")
RecognizerIntent = autoclass("android.speech.RecognizerIntent")
Locale = autoclass("java.util.Locale")

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
