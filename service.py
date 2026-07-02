import os
os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"
from potok import SpeechRecognizer
from GPT import GPT
import uvicorn
import logging
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
import AudioStream
import asyncio
import teststrem
from sound import TextToSpeech

# ================= НАСТРОЙКА ЛОГИРОВАНИЯ =================

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI()

# Глобальные объекты
gpt = GPT()
recognizer = SpeechRecognizer()
tts = TextToSpeech(language="ru")

# ESP32 шлёт голос по UDP на этот порт
UDP_IP = "0.0.0.0"     # слушаем на всех интерфейсах
UDP_PORT = 54321


# ================= ЭНДПОИНТЫ HTTP =================
def _tts_sync(text: str, filename: str) -> str:
    from sound import TextToSpeech
    tts_local = TextToSpeech(language="ru")  # новый engine каждый раз
    return tts_local.text_to_mp3(text, filename)

async def tts_to_file_async(text: str, filename: str) -> str:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _tts_sync, text, filename)
@app.get("/")
async def get_service_status():
    logger.info("===> Проверка статуса сервиса")
    return {"status": "Сервис онлайн"}


@app.post("/gpt/")
async def gpt_endpoint(payload: dict):
    """
    HTTP-эндпоинт, если ты решишь дергать GPT по HTTP.
    Сейчас он не нужен для ESP32, но пусть будет.
    """
    inputs = payload.get("inputs", "")
    logger.info(f"===> /gpt/ payload: {inputs!r}")

    response_text = await gpt.get_responses(inputs=inputs)
    print(response_text)
    # Генерируем temp.wav, чтобы потом отдать его по TCP (teststrem)
    tts.text_to_mp3(response_text, "temp.wav")

    logger.info(f"===> /gpt/ ответ: {response_text!r}")
    return {"text": response_text}


@app.get("/stream")
async def stream_audio():
    """
    HTTP-стрим MP3 (если захочешь слушать через браузер).
    ESP32 сейчас этим не пользуется.
    """
    logger.info("===> /stream — отправка 1.mp3")
    return StreamingResponse(AudioStream.generate_audio_stream(), media_type="audio/mpeg")


# ================= ФОНОВЫЙ ЦИКЛ ГОЛОС → GPT → AUDIO =================

async def voice_loop():
    """
    Бесконечный цикл:
    1) ждёт голос с ESP32 по UDP, распознаёт;
    2) шлёт текст в GPT;
    3) синтезирует речь в temp.wav;
    4) запускает одноразовый TCP-сервер, который отдаёт temp.wav ESP32.
    """
    while True:
        try:
            logger.info("===> Ожидание голосового ввода по UDP...")
            text = await recognizer.run(UDP_IP, UDP_PORT)

            if not text or not text.strip():
                logger.info("===> Ничего не распознано, повторяем цикл")
                continue

            logger.info(f"===> Распознан текст: {text!r}")

            # Получаем ответ от модели
            response_text = await gpt.get_responses(inputs=text)
            logger.info(f"===> Ответ GPT: {response_text!r}")
            if response_text == "":
                response_text = "Я  словила глюк"
            # Синтезируем аудио в temp.wav (именно его читает teststrem.py)
            logger.info("===> TTS start")
            await tts_to_file_async(response_text, "temp.wav")
            logger.info("===> TTS done")
            logger.info("===> Сгенерирован temp.wav для отправки на ESP32")

            # Запускаем одноразовый TCP-сервер, который отдаст temp.wav
            logger.info("===> Старт TCP-сервера для отправки temp.wav")
            await teststrem.start_tcp_server()
            logger.info("===> TCP-сервер закончил работу, ждём следующий голосовой ввод")

        except Exception as e:
            logger.exception(f"Ошибка в voice_loop: {e}")
            # чтобы не словить бешеный цикл ошибок
            await asyncio.sleep(1)


# ================= СТАРТ ФОНОВОЙ ЗАДАЧИ ПРИ ЗАПУСКЕ FASTAPI =================

@app.on_event("startup")
async def startup_event():
    logger.info("===> startup_event: запуск фонового цикла voice_loop")
    asyncio.create_task(voice_loop())


# ================= ТОЧКА ВХОДА =================

if __name__ == "__main__":
    logger.info("===> Запуск сервера Uvicorn...")
    # ВАЖНО: слушаем на 0.0.0.0, чтобы ESP32 мог подключаться
    uvicorn.run(app, host="0.0.0.0", port=7000)
