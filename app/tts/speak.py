import pyttsx3

_engine = None

def _get_engine():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init()
        _engine.setProperty("rate", 180)
    return _engine

def say(text: str):
    try:
        eng = _get_engine()
        eng.say(text)
        eng.runAndWait()
    except Exception:
        # Don’t crash the API if TTS fails
        pass
