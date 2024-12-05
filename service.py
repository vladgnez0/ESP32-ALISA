import os
import uvicorn
import asyncio
import logging
from fastapi import FastAPI, Body,Response
from typing import Dict
from functools import partial
import re
from transformers import AutoTokenizer, AutoModelForCausalLM
from fastapi.responses import StreamingResponse
import wave
import time
import sound
from AudioStream import AudioStreamer
# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()


class GPT:
    def __init__(self):
        self.path_model = 'tinkoff-ai/ruDialoGPT-medium'
        self.tokenizer = None
        self.model = None
        self.history = ''
        self._load_model()

    def _load_model(self):
        logger.info(f"===> Загрузка модели: {self.path_model} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.path_model)
        self.model = AutoModelForCausalLM.from_pretrained(self.path_model)
        logger.info("===> Модель успешно загружена")

    async def get_responses(self, inputs: Dict) -> Dict:
        inputs_text = ''.join(inputs[-1]['text'])
        if inputs[-1]['speaker']== "0":
            self.history += ' @@ПЕРВЫЙ@@ ' + inputs_text + ' @@ВТОРОЙ@@ '

        logger.info(f"===> Текущая история: {self.history}")
        logger.info(f"===> Входной текст: {inputs_text}")

        inputs_token_ids = self.tokenizer.encode(self.history, return_tensors='pt')

        try:
            # Использование partial для передачи всех аргументов
            generate_partial = partial(
                self.model.generate,
                inputs_token_ids,
                top_k=10,
                top_p=0.95,
                num_beams=3,
                num_return_sequences=3,
                do_sample=True,
                no_repeat_ngram_size=2,
                temperature=1.2,
                repetition_penalty=1.2,
                length_penalty=1.0,
                eos_token_id=50257,
                pad_token_id=self.tokenizer.eos_token_id,  # Установка pad_token_id
                max_new_tokens=50
            )

            outputs_token_ids = await asyncio.get_event_loop().run_in_executor(
                None,
                generate_partial
            )
        except Exception as e:
            logger.error(f"===> Ошибка генерации: {str(e)}")
            return {'inputs': '', 'outputs': '', 'status': False, 'msg': f"{str(e)}"}

        outputs = [self.tokenizer.decode(x, skip_special_tokens=True) for x in outputs_token_ids]
        logger.info(f"===> Сгенерированные ответы: {outputs[0]}")

        outputs = [self.tokenizer.decode(x, skip_special_tokens=True) for x in outputs_token_ids]
        logger.info(f"===> Сгенерированные ответы: {outputs[0]}")

        # Поиск последнего вхождения @@ВТОРОЙ@@ и извлечение текста после него
        after_last_vtoroy = re.split(r'@@ВТОРОЙ@@', outputs[0])[-1].strip()
        self.history += after_last_vtoroy
        logger.info(f"===> Обработанный ответ после последнего маркера @@ВТОРОЙ@@: {after_last_vtoroy}")

        # Возвращаем уже очищенные результаты
        return {'inputs': inputs, 'outputs': [after_last_vtoroy], 'status': True, 'msg': ''}


@app.get("/")
async def get_service_status():
    logger.info("===> Проверка статуса сервиса")
    return {"status": "Сервис онлайн"}


@app.post("/gpt/")
async def get_responses(payload: dict = Body(...)):
    inputs = payload.get('inputs', '')
    logger.info(f"===> Получен payload: {inputs}")
    responses = await gpt.get_responses(inputs=inputs)
    logger.info(f"===> Ответ для отправки: {responses}")
    return responses



@app.route('/stream')
def stream_audio():
    def generate_audio():
        # Открытие аудиофайла
        with wave.open("12.wav", "rb") as wf:
            chunk_size = 1024  # Размер блока передачи
            sample_rate = wf.getframerate()  # Частота дискретизации
            bytes_per_second = sample_rate * wf.getsampwidth() * wf.getnchannels()

            while True:
                # Чтение очередного блока
                data = wf.readframes(chunk_size)
                if not data:
                    break  # Конец файла

                # Отправка данных клиенту
                yield data

                # Ограничение скорости передачи
                time.sleep(chunk_size / bytes_per_second)

    response = Response(generate_audio())
    response.mimetype = 'audio/wav'  # Установка mimetype через атрибут
    return response





if __name__ == '__main__':
    #gpt = GPT()
    logger.info("===> Запуск сервера...")
    uvicorn.run(app, host='192.168.137.1', port=5000)
