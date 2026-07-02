import asyncio
import io
from time import sleep

from pydub import AudioSegment

AUDIO_FILE_PATH = "temp.wav"  # Файл с озвучкой, который будет отправлен клиенту
TCP_HOST = "0.0.0.0"          # Прослушивание на всех интерфейсах
TCP_PORT = 12345              # Порт для подключения


async def stream_audio(path: str = AUDIO_FILE_PATH):
    """
    Загружает аудио-файл, конвертирует его в RAW PCM 16kHz mono 16-bit,
    затем добавляет 5 секунд тишины.
    """
    audio = AudioSegment.from_file(path)
    audio = audio.set_frame_rate(16000)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)

    audio_buffer = io.BytesIO()
    audio.export(audio_buffer, format="raw")
    audio_buffer.seek(0)

    # --- основной аудиопоток ---
    while True:
        chunk = audio_buffer.read(1024)
        if not chunk:
            break
        yield chunk

    # --- 5 секунд тишины ---
    print("Добавляем 5 секунд тишины")

    SILENCE_SECONDS = 5
    SAMPLE_RATE = 16000
    BYTES_PER_SAMPLE = 2

    total_silence_bytes = SILENCE_SECONDS * SAMPLE_RATE * BYTES_PER_SAMPLE
    silence_chunk = b"\x00" * 1024

    sent = 0
    while sent < total_silence_bytes:
        yield silence_chunk
        sent += len(silence_chunk)


async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """
    Обрабатывает подключившегося клиента: отправляет ему один раз весь аудиопоток.
    """
    addr = writer.get_extra_info("peername")
    print(f"Клиент подключился: {addr}")

    async for chunk in stream_audio():
        writer.write(chunk)
        await writer.drain()

    print("Отправка аудио завершена, закрываем соединение.")
    writer.close()
    await writer.wait_closed()


async def start_tcp_server(host: str = TCP_HOST, port: int = TCP_PORT):
    """
    Запускает TCP сервер.
    Если в течение 7 секунд никто не подключился — сервер закрывается.
    """
    shutdown_event = asyncio.Event()

    async def _client_handler(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        await handle_client(reader, writer)
        shutdown_event.set()  # Клиент обслужен — закрываем сервер

    server = await asyncio.start_server(_client_handler, host, port)
    addr = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"TCP сервер слушает: {addr}")

    try:
        # ⏱ ждём клиента максимум 7 секунд
        await asyncio.wait_for(shutdown_event.wait(), timeout=7.0)
        print("Клиент подключился — сервер завершается.")
    except asyncio.TimeoutError:
        print("⏱ За 7 секунд никто не подключился. Сервер закрывается.")

    server.close()
    await server.wait_closed()


async def main():
    await start_tcp_server()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Сервер остановлен пользователем")
