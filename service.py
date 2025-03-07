from potok import SpeechRecognizer
from GPT import GPT
import uvicorn
import logging
from fastapi import FastAPI, Body,Response
from fastapi.responses import StreamingResponse
import AudioStream
from sound import TextToSpeech
import asyncio
import teststrem
# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
from typing import Dict
app = FastAPI()
UDP_IP = "192.168.137.1"
UDP_PORT = 12345


from pydantic import BaseModel
@app.get("/")
async def get_service_status():
    logger.info("===> Проверка статуса сервиса")
    return {"status": "Сервис онлайн"}


@app.post("/gpt/")
async  def get_responses(payload: Dict[str, str]):  # payload как обычный словарь
    inputs = payload.get('inputs')  # Теперь get работает корректно, так как payload - словарь
    logger.info(f"===> Получен payload: {inputs}")
    responses = await gpt.get_responses(inputs=inputs)
    tts = TextToSpeech(language='ru')
    tts.text_to_mp3(responses,"1.mp3")
    logger.info(f"===> Ответ для отправки: {responses}")
    return {"message": f"Received: {responses}"}



@app.get("/stream")
async def stream_audio():
    # Отправляем данные как поток с MIME типом audio/mpeg
    logger.info(f"===> Отправка файла на воспроизведение ")
    return StreamingResponse(AudioStream.generate_audio_stream(), media_type="audio/mpeg")
async def main():
    while True:
        result = await recognizer.run(UDP_IP, UDP_PORT)
        responses = await gpt.get_responses(inputs=result)
        try:
            await teststrem.start_tcp_server()
        except Exception as e:
            pass


if __name__ == '__main__':
    gpt = GPT()
    recognizer = SpeechRecognizer()

    asyncio.run(main())
    logger.info("===> Запуск сервера...")
    uvicorn.run(app, host='192.168.137.1', port=7000)
