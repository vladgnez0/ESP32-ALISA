import pyttsx3
from pydub import AudioSegment
import os
import logging
# Настройка логирования
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
class AudioStreamer:
    """
    Класс для потоковой передачи аудио.
    """

    def __init__(self, file_path, chunk_size):
        self.file_path = file_path
        self.chunk_size = chunk_size
        logger.debug(f"AudioStreamer создан с файлом {file_path} и размером блока {chunk_size} байт.")

    def stream(self):
        """
        Потоковое чтение аудиофайла по частям.
        """
        if not os.path.exists(self.file_path):
            logger.error(f"Файл {self.file_path} не найден.")
            raise FileNotFoundError(f"Файл {self.file_path} не найден.")

        logger.info(f"Начало потоковой передачи аудиофайла {self.file_path}")
        try:
            with open(self.file_path, "rb") as f:
                while chunk := f.read(self.chunk_size):
                    #logger.debug(f"Чтение блока данных размером {len(chunk)} байт")
                    yield chunk
        except Exception as e:
            logger.error(f"Ошибка при чтении аудиофайла: {e}")
            raise
