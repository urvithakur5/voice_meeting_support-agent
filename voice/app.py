import os
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

load_dotenv()

SPEECH_KEY = os.getenv("AZURE_SPEECH_KEY")
SPEECH_REGION = os.getenv("AZURE_SPEECH_REGION")

if not SPEECH_KEY or not SPEECH_REGION:
    raise ValueError("Azure Speech credentials are missing from .env")

speech_config = speechsdk.SpeechConfig(
    subscription=SPEECH_KEY,
    region=SPEECH_REGION
)

speech_config.speech_recognition_language = "en-IN"

speech_config.speech_synthesis_voice_name = (
    "en-IN-NeerjaNeural"
)

recognizer = speechsdk.SpeechRecognizer(
    speech_config=speech_config
)

synthesizer = speechsdk.SpeechSynthesizer(
    speech_config=speech_config
)


def speak(text):
    print(f"Agent: {text}")
    synthesizer.speak_text_async(text).get()


def listen():
    print("\nListening...")

    result = recognizer.recognize_once_async().get()

    if result.reason == speechsdk.ResultReason.RecognizedSpeech:
        print(f"You: {result.text}")
        return result.text

    elif result.reason == speechsdk.ResultReason.NoMatch:
        print("Could not understand the speech.")
        return None

    elif result.reason == speechsdk.ResultReason.Canceled:
        cancellation = speechsdk.CancellationDetails.from_result(result)
        print(f"Speech recognition cancelled: {cancellation.reason}")
        print(f"Details: {cancellation.error_details}")
        return None

    return None


def generate_response(user_text):
    text = user_text.lower()

    if "wifi" in text or "internet" in text:
        return (
            "I can help troubleshoot your internet connection. "
            "First, check whether other devices are also unable to connect."
        )

    if "password" in text:
        return (
            "I can help with a password issue. "
            "Please tell me whether you forgot your password "
            "or whether your password is being rejected."
        )

    if "printer" in text:
        return (
            "I can help troubleshoot the printer. "
            "First, check whether the printer is powered on "
            "and connected to the same network."
        )

    if "computer" in text or "laptop" in text:
        return (
            "I can help troubleshoot your computer. "
            "Please describe the problem you are experiencing."
        )

    return (
        "I understood your request. "
        "Please give me a few more details about the IT problem."
    )


speak("Hello. I am your IT helpdesk assistant. How can I help you?")

while True:

    user_text = listen()

    if not user_text:
        continue

    if user_text.lower() in ["exit", "quit", "stop", "goodbye"]:
        speak("Goodbye.")
        break

    response = generate_response(user_text)

    speak(response)
