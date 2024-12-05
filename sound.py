import pyttsx3
import os
import logging
import wave

# Константы для настройки
SAMPLE_RATE = 44100  # Частота дискретизации (Гц)
SAMPLE_WIDTH = 2  # Размер семпла (2 байта = 16 бит)
CHANNELS = 1  # Количество каналов (1 = моно, 2 = стерео)
CONVERTED_FILE = "converted.wav"  # Файл после перекодирования

# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class AudioConverter:
    """
    Класс для конвертации аудиофайлов в WAV с заданными параметрами.
    """

    def __init__(self, input_file, output_file, sample_rate, sample_width, channels):
        self.input_file = input_file
        self.output_file = output_file
        self.sample_rate = sample_rate
        self.sample_width = sample_width
        self.channels = channels
        logger.debug(f"AudioConverter создан с входным файлом: {input_file}, выходным файлом: {output_file}")

    def convert(self):
        """
        Конвертирует аудиофайл в WAV с заданными параметрами.
        """
        if not os.path.exists(self.input_file):
            logger.error(f"Файл {self.input_file} не найден.")
            raise FileNotFoundError(f"Файл {self.input_file} не найден.")

        logger.info(f"Начало конвертации {self.input_file} в {self.output_file}...")

        try:
            with wave.open(self.input_file, 'rb') as input_wav:
                if input_wav.getnchannels() != self.channels or input_wav.getframerate() != self.sample_rate:
                    logger.info(f"Преобразование аудио в требуемые параметры: {self.sample_rate} Гц, {self.channels} канал(ов).")
                    output_audio = wave.open(self.output_file, 'wb')
                    output_audio.setnchannels(self.channels)
                    output_audio.setsampwidth(self.sample_width)
                    output_audio.setframerate(self.sample_rate)
                    frames = input_wav.readframes(input_wav.getnframes())
                    output_audio.writeframes(frames)
                    output_audio.close()
                    logger.info(f"Конвертация завершена: {self.output_file}")
                else:
                    logger.info(f"Файл уже соответствует требуемым параметрам.")
        except Exception as e:
            logger.error(f"Ошибка при конвертации файла: {e}")
            raise

class TextToAudio:
    """
    Класс для преобразования текста в аудио.
    """

    def __init__(self, text, output_file):
        self.text = text
        self.output_file = output_file
        logger.debug(f"TextToAudio создан с текстом: {text[:50]}... и выходным файлом: {output_file}")

    def convert_text_to_audio(self):
        """
        Преобразует текст в аудиофайл и сохраняет его.
        """
        engine = pyttsx3.init()
        logger.info(f"Инициализация синтеза речи для текста: {self.text[:50]}...")

        try:
            engine.setProperty('rate', 150)  # Скорость речи
            engine.setProperty('volume', 1)  # Громкость (от 0.0 до 1.0)
            engine.save_to_file(self.text, self.output_file)
            engine.runAndWait()
            logger.info(f"Текст преобразован в аудио и сохранён в {self.output_file}")
        except Exception as e:
            logger.error(f"Ошибка при преобразовании текста в аудио: {e}")
            raise

def adjust_audio(file_path, output_file, sample_rate=44100, sample_width=2, channels=2):
    """
    Настройка аудиофайла: частота дискретизации, разрядность и количество каналов.
    """
    if not os.path.exists(file_path):
        logger.error(f"Файл {file_path} не найден.")
        raise FileNotFoundError(f"Файл {file_path} не найден.")

    logger.info(f"Настройка параметров аудиофайла {file_path}")
    try:
        with wave.open(file_path, 'rb') as input_audio:
            if input_audio.getnchannels() != channels or input_audio.getframerate() != sample_rate:
                output_audio = wave.open(output_file, 'wb')
                output_audio.setnchannels(channels)
                output_audio.setsampwidth(sample_width)
                output_audio.setframerate(sample_rate)
                frames = input_audio.readframes(input_audio.getnframes())
                output_audio.writeframes(frames)
                output_audio.close()
                logger.info(f"Аудиофайл сохранён с настройками: {sample_rate} Гц, {sample_width * 8}-бит, {channels} канал(а).")
            else:
                logger.info("Файл уже соответствует заданным параметрам.")
    except Exception as e:
        logger.error(f"Ошибка при настройке аудиофайла: {e}")
        raise

# Пример использования
if __name__ == "__main__":
    text = "Привет, как дела?"
    audio_file = "GSPD-Евроденс.wav"  # Исходный файл для текста
    adjusted_file = "output_adjusted.wav"  # Настроенный файл

    # Преобразование текста в аудио
    #text_to_audio = TextToAudio(text, audio_file)
    #text_to_audio.convert_text_to_audio()

    # Настройка параметров аудиофайла
    adjust_audio(audio_file, adjusted_file, sample_rate=44100, sample_width=2, channels=1)
