import os
import sys
import asyncio
import json
import vosk
import queue


# Укажите путь к вашей модели
MODEL_PATH = "model/vosk-model-small-ru-0.22"  # Путь к модели Vosk

class SpeechRecognizer:
    def __init__(self, model_path=MODEL_PATH, rate=16000, buffer_size=8000):
        self.model_path = model_path
        self.rate = rate
        self.buffer_size = buffer_size
        self.model = None
        self.recognizer = None
        self.audio_queue = asyncio.Queue()  # Асинхронная очередь для аудиоданных

    def load_model(self):
        """Загружает модель Vosk."""
        if not os.path.exists(self.model_path):
            print(f"Модель не найдена по пути: {self.model_path}")
            sys.exit(1)
        self.model = vosk.Model(self.model_path)
        print("Модель загружена.")

    def initialize_recognizer(self):
        """Инициализирует распознаватель речи."""
        if self.model is None:
            raise ValueError("Модель не загружена. Сначала вызовите load_model().")
        self.recognizer = vosk.KaldiRecognizer(self.model, self.rate)
        print("Распознаватель инициализирован.")

    async def listen_and_recognize(self):
        """Распознает речь из аудиоданных, поступающих из очереди."""
        if self.recognizer is None:
            raise ValueError("Распознаватель не инициализирован. Сначала вызовите initialize_recognizer().")

        print("Слушаю... Пожалуйста, говорите.")

        buffer = b""  # Буфер для накопления данных

        while True:
            try:
                data = await self.audio_queue.get()  # Асинхронное получение данных из очереди
                buffer += data  # Добавляем данные в буфер

                # Если в буфере достаточно данных, обрабатываем их
                if len(buffer) >= self.buffer_size:
                    print(buffer)
                    if self.recognizer.AcceptWaveform(buffer[:self.buffer_size]):
                        result = self.recognizer.Result()
                        print(f"Распознано: {result}")

                        if "алиса" in result:
                            # Преобразуем строку в словарь
                            data = json.loads(result)
                            # Извлекаем текст из поля "text"
                            recognized_text = data.get("text", "")
                            print(f"Распознанная команда: {recognized_text}")
                            return recognized_text

                    buffer = buffer[self.buffer_size:]  # Убираем обработанные данные из буфера
            except queue.Empty:
                await asyncio.sleep(0.1)  # Если очередь пуста, ждем немного

    async def run(self, udp_ip, udp_port):
        self.load_model()
        self.initialize_recognizer()

        loop = asyncio.get_running_loop()
        transport = None  # Добавляем переменную для транспорта

        try:
            # Создаем UDP-сервер
            transport, protocol = await loop.create_datagram_endpoint(
                lambda: UDPProtocol(self.audio_queue),
                local_addr=(udp_ip, udp_port)
            )
            print(f"Слушаю UDP-поток на {udp_ip}:{udp_port}...")

            # Запускаем распознавание речи
            return await self.listen_and_recognize()
        finally:
            if transport:  # Явно закрываем транспорт при завершении
                transport.close()

class UDPProtocol:
    def __init__(self, audio_queue):
        self.audio_queue = audio_queue

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        """Обрабатывает полученные UDP-пакеты."""
        #print(f"Получено данных: {len(data)} байт от {addr}")
        self.audio_queue.put_nowait(data)  # Помещаем данные в очередь

    def error_received(self, exc):
        print(f"Ошибка при получении данных: {exc}")

    def connection_lost(self, exc):
        print("Соединение закрыто.")

# Настройки UDP
UDP_IP = "192.168.137.1"
UDP_PORT = 12345
async def main():
    recognizer = SpeechRecognizer()
    result = asyncio.run(recognizer.run(UDP_IP, UDP_PORT))


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    recognizer = SpeechRecognizer()
    result = asyncio.run(recognizer.run(UDP_IP, UDP_PORT))
    print(result)
