# sound.py — Piper TTS (стабильный, офлайн)
import subprocess
import os
import tempfile

class TextToSpeech:
    """
    Drop-in TTS.
    Совместим с твоим service.py:
    text_to_mp3(text, "temp.wav")
    """

    def __init__(self, language: str = "ru"):
        base_dir = os.path.dirname(__file__)

        self.piper_exe = os.path.join(base_dir, "piper", "piper.exe")
        self.model = os.path.join(
            base_dir,
            "piper",
            "models",
            "ru-irinia-medium.onnx"  # ← если модель другая — поменяй имя
        )

        if not os.path.exists(self.piper_exe):
            raise FileNotFoundError(f"Piper не найден: {self.piper_exe}")
        if not os.path.exists(self.model):
            raise FileNotFoundError(f"Модель не найдена: {self.model}")

    def text_to_mp3(self, text: str, output_filename: str = "temp.wav") -> str:
        text = (text or "").strip()
        if not text:
            text = "Скажи ещё раз, пожалуйста."

        # Piper принимает текст через stdin
        cmd = [
            self.piper_exe,
            "-m", self.model,
            "-f", output_filename
        ]

        proc = subprocess.run(
            cmd,
            input=text.encode("utf-8"),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        if proc.returncode != 0:
            err = proc.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"Piper error: {err}")

        return output_filename


# Быстрый тест
if __name__ == "__main__":
    tts = TextToSpeech()
    tts.text_to_mp3("Привет! Это тест Piper.", "test.wav")
    print("OK")
