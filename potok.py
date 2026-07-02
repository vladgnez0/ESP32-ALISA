import asyncio
import json
import vosk

MODEL_PATH = "model/vosk-model-small-ru-0.22"  # Путь к модели Vosk


class AudioReceiverProtocol(asyncio.DatagramProtocol):
    """
    Принимает UDP-пакеты с аудио и складывает их в очередь.
    Если очередь переполнена — тихо дропает пакеты (лучше, чем падать).
    """

    def __init__(self, audio_queue: asyncio.Queue):
        super().__init__()
        self.audio_queue = audio_queue

    def datagram_received(self, data: bytes, addr):
        try:
            self.audio_queue.put_nowait(data)
        except asyncio.QueueFull:
            # Дроп пакета при переполнении очереди
            pass

    def error_received(self, exc):
        print(f"Ошибка при приёме датаграммы: {exc}")

    def connection_lost(self, exc):
        print("UDP-соединение закрыто.")


class SpeechRecognizer:
    def __init__(
        self,
        model_path: str = MODEL_PATH,
        rate: int = 16000,
        buffer_size: int = 8000,
        queue_maxsize: int = 500,
        keyword: str = "кубик",
    ):
        self.model_path = model_path
        self.rate = rate
        self.buffer_size = buffer_size
        self.queue_maxsize = queue_maxsize
        self.keyword = (keyword or "").strip().lower()

        self.model: vosk.Model | None = None
        self.recognizer: vosk.KaldiRecognizer | None = None

        self.audio_queue: asyncio.Queue = asyncio.Queue(maxsize=self.queue_maxsize)
        self.transport = None
        self.protocol = None

    def load_model(self) -> None:
        if self.model is None:
            print("Загрузка модели Vosk...")
            self.model = vosk.Model(self.model_path)
            print("Модель загружена.")

    def initialize_recognizer(self) -> None:
        if self.model is None:
            raise ValueError("Модель не загружена. Сначала вызовите load_model().")
        if self.recognizer is None:
            self.recognizer = vosk.KaldiRecognizer(self.model, self.rate)
            print("Распознаватель инициализирован.")

    def _reset_recognizer(self) -> None:
        # Важно сбрасывать между фразами, чтобы не тянуло хвосты предыдущей речи
        if self.recognizer is not None:
            try:
                self.recognizer.Reset()
            except Exception:
                pass

    def _drain_queue(self) -> None:
        # Перед новым циклом слушания чистим очередь, чтобы не всплывали старые пакеты
        try:
            while True:
                self.audio_queue.get_nowait()
        except asyncio.QueueEmpty:
            pass

    async def start_udp(self, udp_ip: str, udp_port: int) -> None:
        """
        Поднимает UDP endpoint ОДИН РАЗ.
        Если уже запущен — ничего не делает.
        """
        if self.transport is not None:
            return

        self.load_model()
        self.initialize_recognizer()

        loop = asyncio.get_running_loop()
        self.audio_queue = asyncio.Queue(maxsize=self.queue_maxsize)

        self.transport, self.protocol = await loop.create_datagram_endpoint(
            lambda: AudioReceiverProtocol(self.audio_queue),
            local_addr=(udp_ip, udp_port),
        )
        print(f"UDP сервер запущен на {udp_ip}:{udp_port}")

    async def stop_udp(self) -> None:
        """
        Останавливает UDP endpoint (обычно не нужно делать в основном цикле).
        """
        if self.transport is not None:
            self.transport.close()
            self.transport = None
            self.protocol = None
            print("UDP сервер остановлен.")

    async def listen_and_recognize(
            self,
            *,
            silence_timeout_sec: float = 2.0,
            max_phrase_sec: float = 15.0,  # лимит на фразу ПОСЛЕ старта речи
            max_wait_for_speech_sec: float = 0,  # 0 = ждать бесконечно, пока не начнут говорить
            return_on_keyword: bool = False,
    ) -> str:
        """
        Ждёт аудио из очереди и распознаёт.

        Отличия от старой версии:
        - НЕ возвращает "" каждые N секунд, если речи нет (если max_wait_for_speech_sec=0)
        - старт таймера фразы — после первого аудио-пакета
        - очередь НЕ чистим (чтобы не терять начало фразы)
        - сбрасываем recognizer между фразами
        """
        if self.recognizer is None:
            raise ValueError("Распознаватель не инициализирован. Сначала вызовите start_udp().")

        self._reset_recognizer()

        print("Слушаю... говорите (желательно со словом 'кубик').")

        buffer = b""
        last_final_text = ""

        loop = asyncio.get_running_loop()

        speech_started_at = None  # время, когда пришёл первый пакет речи
        last_audio_t = loop.time()
        wait_started_at = loop.time()

        while True:
            # Если задан лимит ожидания начала речи — можно выйти пусто
            if max_wait_for_speech_sec and (loop.time() - wait_started_at) > max_wait_for_speech_sec:
                return ""

            try:
                data = await asyncio.wait_for(self.audio_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                # если речь уже началась и наступила тишина — возвращаем последнее финальное
                if speech_started_at is not None:
                    if (loop.time() - last_audio_t) > silence_timeout_sec and last_final_text.strip():
                        self._reset_recognizer()
                        return last_final_text.strip()
                continue

            now = loop.time()
            last_audio_t = now

            # старт фразы после первого пакета
            if speech_started_at is None:
                speech_started_at = now

            # лимит длительности фразы (после старта речи)
            if (now - speech_started_at) > max_phrase_sec:
                self._reset_recognizer()
                return last_final_text.strip()

            buffer += data

            # обрабатываем накопленное
            while len(buffer) >= self.buffer_size:
                chunk = buffer[:self.buffer_size]
                buffer = buffer[self.buffer_size:]

                if self.recognizer.AcceptWaveform(chunk):
                    try:
                        result = json.loads(self.recognizer.Result())
                    except json.JSONDecodeError:
                        continue

                    recognized_text = (result.get("text") or "").strip()
                    if recognized_text:
                        last_final_text = recognized_text
                        print(f"Распознано: {recognized_text}")

                        if return_on_keyword and self.keyword and (self.keyword in recognized_text.lower()):
                            self._reset_recognizer()
                            return recognized_text



    async def run(self, udp_ip: str, udp_port: int) -> str:
        """
        Совместимость со старым service.py:
        - НЕ делает bind каждый раз
        - UDP стартует один раз
        - потом просто слушаем и возвращаем текст
        """
        await self.start_udp(udp_ip, udp_port)
        return await self.listen_and_recognize()


# --- Тестовый запуск (не нужен в сервисе) ---
UDP_IP = "0.0.0.0"
UDP_PORT = 54321

async def main():
    recognizer = SpeechRecognizer()
    await recognizer.start_udp(UDP_IP, UDP_PORT)

    while True:
        text = await recognizer.listen_and_recognize(return_on_keyword=False)
        print("Результат распознавания:", text)

if __name__ == "__main__":
    asyncio.run(main())
