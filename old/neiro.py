import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
import logging

# Настройка логгера для контроля вывода информации
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Определяем устройство: используем GPU, если доступно, иначе CPU
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
# Устанавливаем количество потоков для выполнения на CPU
torch.set_num_threads(4)


class EbankoBot:
    def __init__(self):
        model_path = "../ESP32-ALISA/model/"  # Проверьте правильность пути к модели
        logger.info(f"Инициализация бота. Используем модель из: {model_path}")

        try:
            # Загружаем токенизатор
            self.tokenizer = AutoTokenizer.from_pretrained(model_path)
            logger.info("Токенизатор успешно загружен.")
        except Exception as e:
            logger.error(f"Ошибка при загрузке токенизатора: {e}")
            raise

        try:
            # Загружаем модель
            self.model = AutoModelForCausalLM.from_pretrained(model_path)
            logger.info("Модель успешно загружена.")
        except Exception as e:
            logger.error(f"Ошибка при загрузке модели: {e}")
            raise

        # Изменяем размер эмбеддингов модели в соответствии с токенизатором
        self.model.resize_token_embeddings(len(self.tokenizer))
        logger.info("Размер эмбеддингов модели изменен в соответствии с токенизатором.")

        # Параметры для генерации текста
        self.gen_kwargs = {
            "min_length": 101,  # Увеличено для более содержательных ответов
            "max_new_tokens": 100,
            "top_k": 100,
            "top_p": 0.9,
            "do_sample": True,
            "early_stopping": True,
            'temperature': 0.6,
            "no_repeat_ngram_size": 4,
            "eos_token_id": self.tokenizer.eos_token_id,
            "pad_token_id": self.tokenizer.pad_token_id,
            "use_cache": True,
            "repetition_penalty": 1.5,
            "length_penalty": 1.2,
            "num_beams": 4,  # Параметр beam search
            "num_return_sequences": 1,  # Возвращаем только одну последовательность
        }
        logger.info("Параметры генерации текста инициализированы.")

        # Переносим модель на выбранное устройство (CPU или GPU)
        self.model.to(DEVICE)

        # Применяем динамическое квантование для повышения производительности на CPU
        self.model = torch.quantization.quantize_dynamic(self.model, {torch.nn.Linear}, dtype=torch.qint8)
        logger.info(f"Модель перенесена на устройство: {DEVICE}")

    def generation_text(self, q=""):
        if not q.strip():
            logger.warning("Получен пустой запрос.")
            return "Запрос не должен быть пустым."

        # Токенизируем входной текст и переносим на выбранное устройство
        logger.info(f"Получен вопрос: {q}")
        t = self.tokenizer.encode(f'{q}', return_tensors='pt').to(DEVICE)
        logger.info(f"Токенизированный запрос: {t}")

        try:
            # Генерация текста с использованием заданных параметров
            g = self.model.generate(t, **self.gen_kwargs)
            generated_text = self.tokenizer.decode(g[0], skip_special_tokens=True)
            logger.info(f"Сгенерированный текст: {generated_text}")
        except Exception as e:
            logger.error(f"Ошибка при генерации текста: {e}")
            return "Произошла ошибка при генерации ответа."

        # Определение длины сгенерированного текста
        length_rep = len(self.tokenizer.encode(generated_text))
        if length_rep <= 15:
            length_param = '1'
        elif length_rep <= 50:
            length_param = '2'
        elif length_rep <= 256:
            length_param = '3'
        else:
            length_param = '-'

        # Формирование строки для дальнейшей генерации (если необходимо)
        inputs_text = f"|0|{length_param}|{generated_text}|1|{256}|"
        logger.info(f"Строка для повторной генерации: {inputs_text}")

        # Токенизация строки для дальнейшей генерации
        inputs_token_ids = self.tokenizer.encode(inputs_text, return_tensors='pt').to(DEVICE)

        try:
            # Повторная генерация с увеличенным max_length
            outputs_token_ids = self.model.generate(
                inputs_token_ids,
                max_length=256,  # Увеличенное значение max_length
                no_repeat_ngram_size=4,
                top_k=100,
                top_p=0.9,
                temperature=0.6,
                num_beams=4,
                early_stopping=True,

                do_sample=False
            )
            outputs = [self.tokenizer.decode(x, skip_special_tokens=True) for x in outputs_token_ids]
            logger.info(f"Извлеченный ответ: {outputs}")
        except Exception as e:
            logger.error(f"Ошибка при повторной генерации текста: {e}")
            return "Произошла ошибка при повторной генерации ответа."

        # Возвращаем сгенерированные ответы
        return outputs
