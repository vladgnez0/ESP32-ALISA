import pyttsx3
from pydub import AudioSegment
import os


class TextToSpeech:
    def __init__(self, language='en'):
        self.language = language
        self.engine = pyttsx3.init()

    def set_language(self):
        # Устанавливаем язык для синтезатора
        voices = self.engine.getProperty('voices')
        if self.language == 'ru':
            # Выбираем русский голос
            for voice in voices:

                if 'HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_RU-RU_IRINA_11.0' in voice.id:
                    self.engine.setProperty('voice', voice.id)
                    break
        else:
            # Для других языков, например, английский
            self.engine.setProperty('voice', voices[1].id)

    def text_to_mp3(self, text, output_filename="output.mp3"):
        """
        Преобразует текст в аудиофайл MP3 локально.

        :param text: Текст для синтеза речи.
        :param output_filename: Имя выходного файла.
        :return: Путь к сохраненному MP3 файлу.
        """
        # Устанавливаем язык
        self.set_language()

        # Сохраняем аудиофайл во временный wav
        temp_wav = "temp.wav"
        self.engine.save_to_file(text, temp_wav)
        self.engine.runAndWait()

        # Преобразуем wav в mp3 с помощью pydub
        audio = AudioSegment.from_wav(temp_wav)
        audio.export(output_filename, format="mp3")

        # Удаляем временный файл
        #os.remove(temp_wav)

        return output_filename


# Пример использования
if __name__ == "__main__":
    tts = TextToSpeech(language='ru')  # Для русского языка
    text = "Привет, это пример локального синтеза речи на Python!"
    output_file = tts.text_to_mp3(text, "local_speech.mp3")
    print(f"MP3 файл сохранен как {output_file}")
