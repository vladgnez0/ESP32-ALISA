import asyncio
import logging
import re
from functools import partial
from typing import Optional

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "gpt")
# Настройка логирования
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class GPT:
    """
    Обёртка над моделью из transformers, заточенная под диалог на русском.
    """

    def __init__(self, model_name: str = "model/gptmedium"):
        # Здесь можно указать ваш путь к локальной модели
        self.path_model = model_name
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        self.history: str = ""
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

    def extract_cube_word(self, text: str) -> str:
        """
        Удаляет слово 'кубик' (во всех падежах) из текста.
        """
        pattern = r"\bкубик(?:а|у|ом|е|и|ов|ам|ами|ах)?\b"
        return text #re.sub(pattern, "", text, flags=re.IGNORECASE)

    def _clean_text(self, text: str) -> str:
        """
        Очищает текст от лишних символов, оставляя только разумный набор.
        """
        text = re.sub(r'[^а-яА-ЯёЁa-zA-Z0-9\s\.,!?—\-()":;\n]', "", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _load_model(self) -> None:
        """
        Ленивая загрузка модели и токенизатора (ТОЛЬКО офлайн).
        """
        if self.tokenizer is not None and self.model is not None:
            return

        import os
        from transformers import AutoTokenizer, AutoModelForCausalLM

        # Нормализуем путь (на случай относительного)
        local_path = os.path.abspath(self.path_model)

        # Быстрая проверка, что это реально папка с моделью
        if not os.path.isdir(local_path):
            raise FileNotFoundError(f"Папка модели не найдена: {local_path}")

        logger.info(f"===> Офлайн-загрузка модели из: {local_path}")

        try:
            # local_files_only=True запрещает любые обращения в интернет
            self.tokenizer = AutoTokenizer.from_pretrained(
                local_path,
                local_files_only=True
            )
            self.model = AutoModelForCausalLM.from_pretrained(
                local_path,
                local_files_only=True
            )
        except Exception as e:
            raise RuntimeError(
                "Не удалось загрузить модель ОФЛАЙН. "
                "Проверь, что в папке есть как минимум config.json и веса (pytorch_model.bin или *.safetensors), "
                "а также файлы токенизатора (tokenizer.json или vocab.json/merges.txt). "
                f"Путь: {local_path}. Ошибка: {e}"
            )

        self.model.to(self.device)
        self.model.eval()
        logger.info("===> Модель успешно загружена (offline)")

    async def get_responses(self, inputs):
        self._load_model()
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

        # Возвращаем уже очищенные результаты
        #return {'inputs': inputs, 'outputs': outputs, 'status': True, 'msg': ''}
        return  cleaned_text
