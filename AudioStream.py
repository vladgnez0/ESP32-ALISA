# import os
#
# import logging
#
# import wave
# import time
# from typing import Dict
# # Настройка логирования
# logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# logger = logging.getLogger(__name__)
# class AudioStreamer:
#     """
#     Класс для потоковой передачи аудио.
#     """
#
#     def __init__(self, file_path: str, chunk_size: int = 1024):
#         self.file_path = file_path
#         self.chunk_size = chunk_size
#         logger.debug(f"AudioStreamer создан с файлом {file_path} и размером блока {chunk_size} байт.")
#
#     def stream(self):
#         """
#         Потоковое чтение аудиофайла по частям.
#         """
#         if not os.path.exists(self.file_path):
#             logger.error(f"Файл {self.file_path} не найден.")
#             raise FileNotFoundError(f"Файл {self.file_path} не найден.")
#
#         logger.info(f"Начало потоковой передачи аудиофайла {self.file_path}")
#         try:
#             with wave.open(self.file_path, "rb") as wf:
#                 sample_rate = wf.getframerate()
#                 bytes_per_second = sample_rate * wf.getsampwidth() * wf.getnchannels()
#
#                 while True:
#                     # Чтение очередного блока данных
#                     data = wf.readframes(self.chunk_size)
#                     if not data:
#                         break
#                     # Ограничение скорости передачи
#                     time.sleep(self.chunk_size / bytes_per_second)
#                     yield data
#         except Exception as e:
#             logger.error(f"Ошибка при чтении аудиофайла: {e}")
#             raise
import aiofiles
MP3_FILE_PATH = '1.mp3'
async def generate_audio_stream():
    async with aiofiles.open(MP3_FILE_PATH, 'rb') as f:
        while True:
            chunk = await f.read(1024)  # Читаем файл частями по 1024 байта
            if not chunk:
                break
            yield chunk
