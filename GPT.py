
import asyncio
import logging
from sound import TextToSpeech
from typing import Dict
from functools import partial
import re
from transformers import AutoTokenizer, AutoModelForCausalLM

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GPT:
    def __init__(self):
        self.path_model = 'tinkoff-ai/ruDialoGPT-medium'
        self.tokenizer = None
        self.model = None
        self.history = ''
        self._load_model()
        self.tts = TextToSpeech(language='ru')

    def _load_model(self):
        logger.info(f"===> Загрузка модели: {self.path_model} ...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.path_model)
        self.model = AutoModelForCausalLM.from_pretrained(self.path_model)
        logger.info("===> Модель успешно загружена")

    async def get_responses(self, inputs: Dict) -> Dict:
        print(inputs)
        inputs_text = inputs
        print(inputs_text)
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

        logger.info(f"===> Обработанный ответ после последнего маркера @@ВТОРОЙ@@: {after_last_vtoroy}")

        # Добавьте этот код после извлечения after_last_vtoroy
        cleaned_text = re.sub(
            r'[^а-яА-ЯёЁ\s\.,!?—\-()":;\n]',  # Разрешенные символы
            '',
            after_last_vtoroy
        )

        # Дополнительная очистка лишних пробелов
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        self.history += cleaned_text

        self.tts.text_to_mp3(cleaned_text)
        # Возвращаем уже очищенные результаты
        #return {'inputs': inputs, 'outputs': outputs, 'status': True, 'msg': ''}
        return  cleaned_text
