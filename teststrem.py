import asyncio
import io
from pydub import AudioSegment

AUDIO_FILE_PATH = "sample-15s.wav"  # Исходный аудиофайл
TCP_HOST = "0.0.0.0"  # Прослушивание на всех интерфейсах
TCP_PORT = 12345  # Порт для подключения

# Преобразование аудио в нужный формат (16000 Гц, 16 бит, моно)
async def stream_audio():
    audio = AudioSegment.from_file("temp.wav")
    audio = audio.set_frame_rate(16000)  # Частота дискретизации 16000 Гц
    audio = audio.set_channels(1)  # Моно
    audio = audio.set_sample_width(2)  # 16 бит (2 байта на sample)
    audio_buffer = io.BytesIO()
    audio.export(audio_buffer, format="raw")
    audio_buffer.seek(0)

    while True:
        chunk = audio_buffer.read(1024)
        if not chunk:
            break  # Завершаем генератор, когда данные закончились
        await asyncio.sleep(0.02)  # Асинхронная задержка, не блокирующая другие операции
        yield chunk

# Обработка подключения и передача аудио
async def handle_client(reader, writer, shutdown_event):
    try:
        # Передача аудио данных по TCP
        async for chunk in stream_audio():
            writer.write(chunk)  # Отправляем данные клиенту
            await writer.drain()  # Асинхронная отправка данных

        print("Все данные переданы.")
    except Exception as e:
        print(f"Ошибка при передаче данных: {e}")
    finally:
        # Закрытие соединения
        writer.close()
        await writer.wait_closed()
        print("Соединение закрыто.")

        # После первого подключения вызываем событие для завершения работы сервера
        shutdown_event.set()

# Запуск асинхронного TCP-сервера
async def start_tcp_server():
    shutdown_event = asyncio.Event()  # Событие для завершения работы сервера

    server = await asyncio.start_server(
        lambda reader, writer: handle_client(reader, writer, shutdown_event),  # Передаем shutdown_event
        TCP_HOST,
        TCP_PORT
    )
    print(f"Сервер запущен на {TCP_HOST}:{TCP_PORT}. Ожидаем подключений...")

    async with server:
        # Ожидаем события завершения работы после первого подключения
        await shutdown_event.wait()
        print("Первое подключение завершено. Завершаем работу сервера.")
        server.close()  # Закрываем сервер
        await server.wait_closed()  # Ожидаем завершения

# Главная функция для запуска сервера
async def main():
    await start_tcp_server()  # Запуск сервера

if __name__ == "__main__":
    try:
        asyncio.run(main())  # Запуск асинхронного сервера
    except KeyboardInterrupt:
        print("Сервер остановлен пользователем")
