#include "Arduino.h"
#include <WiFi.h>
#include <WiFiUdp.h>
#include <driver/i2s.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <math.h>
#include  <oled.h>
// ================== НАСТРОЙКИ ==================

// Touch sensor pin (TTP223 с цифровым выходом)
#define TOUCH_PIN 4  // GPIO для TTP223

// WiFi настройки
const char* ssid     = "Arduino";
const char* password = "12345678";

// Сервер (должен совпадать с твоим Python-сервисом)
const char* serverIP   = "192.168.137.1";
const int   serverPort = 12345;  // UDP для записи и TCP для воспроизведения
const int serverUdp = 54321;
// Объект для UDP (передача голоса на сервер)
WiFiUDP udp;

// Глобальная переменная для аудиоданных микрофона
int16_t samples[4000];

// Пины I²S для микрофона INMP441
#define I2S_MIC_WS   15
#define I2S_MIC_SCK  14
#define I2S_MIC_SD   32

// Пины I²S для динамика
#define I2S_WS 26
#define I2S_SCK 27
#define I2S_SD 25

// Дескриптор задачи микрофона
TaskHandle_t audioTaskHandle = NULL;

// Флаги работы
volatile bool isRecording      = false;  // записываем ли сейчас микрофон
volatile bool playRequested    = false;  // надо ли после записи воспроизвести ответ

// Как долго писать по одному нажатию (мс)
const unsigned long RECORD_DURATION_MS = 5000;  // 5 секунд на фразу
unsigned long recordStartMs = 0;

// ================== НАСТРОЙКА I2S ==================

void setupI2S_Speaker() {
    i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_TX),
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_I2S_MSB,
        .intr_alloc_flags = ESP_INTR_FLAG_LEVEL1,
        .dma_buf_count = 32,
        .dma_buf_len = 1024,
        .use_apll = true
    };

    const i2s_pin_config_t pin_config = {
        .bck_io_num   = I2S_SCK,
        .ws_io_num    = I2S_WS,
        .data_out_num = I2S_SD,
        .data_in_num  = I2S_PIN_NO_CHANGE
    };

    esp_err_t err = i2s_driver_install(I2S_NUM_1, &i2s_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("I2S установка ошибка: %d\n", err);
        setUiError("I2S spk install");
        renderEyes(uiState);
        return;
    }

    err = i2s_set_pin(I2S_NUM_1, &pin_config);
    if (err != ESP_OK) {
        Serial.printf("I2S настройка пинов ошибка: %d\n", err);
        setUiError("I2S mic install");
        renderEyes(uiState);
        return;
    }

    Serial.println("I2S для динамика настроен");
}

void setupI2S_Microphone() {
    const i2s_config_t i2s_config = {
        .mode = (i2s_mode_t)(I2S_MODE_MASTER | I2S_MODE_RX),
        .sample_rate = 16000,
        .bits_per_sample = I2S_BITS_PER_SAMPLE_16BIT,
        .channel_format = I2S_CHANNEL_FMT_ONLY_LEFT,
        .communication_format = I2S_COMM_FORMAT_STAND_I2S,
        .intr_alloc_flags = 0,
        .dma_buf_count = 8,
        .dma_buf_len = 1024,
        .use_apll = false
    };

    const i2s_pin_config_t pin_config = {
        .bck_io_num   = I2S_MIC_SCK,
        .ws_io_num    = I2S_MIC_WS,
        .data_out_num = I2S_PIN_NO_CHANGE,
        .data_in_num  = I2S_MIC_SD
    };

    esp_err_t err = i2s_driver_install(I2S_NUM_0, &i2s_config, 0, NULL);
    if (err != ESP_OK) {
        Serial.printf("Ошибка установки драйвера I²S: %d\n", err);
        return;
    }

    err = i2s_set_pin(I2S_NUM_0, &pin_config);
    if (err != ESP_OK) {
        Serial.printf("Ошибка настройки пинов I²S: %d\n", err);
        return;
    }

    Serial.println("I²S для микрофона настроен успешно");
}

// ================== ЗАДАЧА ЗАПИСИ (МИКРОФОН → UDP) ==================

void audioTask(void *pvParameters) {
    static uint32_t packet_counter = 0;

    while (1) {
        if (isRecording) {
            // Читаем микрофон и отправляем по UDP
            size_t bytes_read = 0;
            esp_err_t err = i2s_read(I2S_NUM_0, &samples, sizeof(samples), &bytes_read, portMAX_DELAY);
            if (err != ESP_OK) {
                Serial.printf("Ошибка чтения I²S (микрофон): %d\n", err);
                vTaskDelay(pdMS_TO_TICKS(20));
                continue;
            }

            udp.beginPacket(serverIP, serverUdp);
            udp.write((uint8_t*)samples, bytes_read);
            udp.endPacket();

            packet_counter++;
            Serial.printf("Отправлено пакетов: %d, байт: %d\n", packet_counter, (int)bytes_read);
        } else {
            // Не записываем — чуть спим
            vTaskDelay(pdMS_TO_TICKS(50));
        }
    }
}

// ================== ТЕСТ ДИНАМИКА ==================

#define TEST_TONE_FREQUENCY 1000   // Частота тестового сигнала (1000 Гц)
#define SAMPLE_RATE         16000  // Частота дискретизации (16000 Гц)
#define AMPLITUDE           3000   // Амплитуда тестового сигнала
#define TEST_DURATION       2      // Длительность теста в секундах

void generateTestTone(int16_t *buffer, size_t bufferSize) {
    static float phase = 0.0f;
    float phaseIncrement = (2.0f * M_PI * TEST_TONE_FREQUENCY) / SAMPLE_RATE;

    for (size_t i = 0; i < bufferSize; i++) {
        buffer[i] = (int16_t)(AMPLITUDE * sinf(phase));
        phase += phaseIncrement;
        if (phase > 2.0f * M_PI) {
            phase -= 2.0f * M_PI;
        }
    }
}

void testSpeaker() {
    int16_t buffer[1024];

    size_t samplesToSend = TEST_DURATION * SAMPLE_RATE;
    size_t samplesSent   = 0;

    Serial.println("Запуск теста динамика...");

    while (samplesSent < samplesToSend) {
        size_t bytesWritten      = 0;
        size_t remainingSamples  = samplesToSend - samplesSent;
        size_t samplesToWrite    = min(sizeof(buffer) / sizeof(buffer[0]), remainingSamples);

        generateTestTone(buffer, samplesToWrite);

        esp_err_t err = i2s_write(I2S_NUM_1, buffer, samplesToWrite * sizeof(int16_t), &bytesWritten, portMAX_DELAY);
        if (err != ESP_OK) {
            Serial.printf("Ошибка воспроизведения через I2S: %d\n", err);
            return;
        }

        samplesSent += samplesToWrite;
        delay(50);
    }

    i2s_zero_dma_buffer(I2S_NUM_1);
    Serial.println("Тест динамика завершен!");
}

// ================== ГРОМКОСТЬ ==================

void reduceVolume(int16_t* buffer, int length, float factor) {
    for (int i = 0; i < length; i++) {
        buffer[i] = (int16_t)(buffer[i] * factor);
    }
}

// ================== ВОСПРОИЗВЕДЕНИЕ ОТВЕТА (TCP → I2S) ==================

void playAudioOnceFromServer() {
    WiFiClient client;

    Serial.println("Ожидание подключения к серверу для воспроизведения...");

    const int retryDelayMs = 500;
    const int maxRetries   = 40;   // 40 * 500мс = ~20 секунд
    int retries = 0;

    // Ждём, пока TCP-сервер появится (но не вечно)
    while (!client.connect(serverIP, serverPort)) {
        retries++;
        Serial.printf("Сервер недоступен, попытка %d/%d\n", retries, maxRetries);

        if (retries >= maxRetries) {
            setUiError("Server timeout");
            renderEyes(uiState);
            Serial.println("Сервер не появился за отведённое время — отмена воспроизведения");
            client.stop();
            return;
        }

        delay(retryDelayMs);
    }

    Serial.println("Соединение для воспроизведения установлено.");

    int16_t buffer[1024];            // буфер PCM 16-bit
    const float volumeFactor = 0.9f; // громкость

    // Читаем, пока сервер шлёт данные
    while (client.connected() || client.available()) {
        int available = client.available();

        if (available > 0) {
            int toRead = min(available, (int)sizeof(buffer));
            int bytesRead = client.read((uint8_t*)buffer, toRead);

            if (bytesRead > 0) {
                int samplesCount = bytesRead / sizeof(int16_t);
                reduceVolume(buffer, samplesCount, volumeFactor);

                size_t bytesWritten = 0;
                esp_err_t err = i2s_write(
                    I2S_NUM_1,
                    buffer,
                    bytesRead,
                    &bytesWritten,
                    portMAX_DELAY
                );

                if (err != ESP_OK) {
                    Serial.printf("Ошибка воспроизведения через I2S: %d\n", err);
                    break;
                }
            }
        } else {
            // Нет данных — подождём немного
            delay(10);
        }
    }

    i2s_zero_dma_buffer(I2S_NUM_1);
    client.stop();
    Serial.println("Воспроизведение завершено, соединение закрыто.");
}

// ================== SETUP & LOOP ==================

void setup() {
    Serial.begin(115200);
    Serial.println("\nЗапуск...");

    // Подключение к WiFi
    WiFi.begin(ssid, password);
    Serial.print("Подключение к WiFi");
     // OLED init
    u8g2.begin();
    setUiState(UI_WIFI_CONNECTING);
    renderEyes(uiState);

    uint32_t t0 = millis();
    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
                // если хочешь таймаут (например 20 сек) -> ошибка на экран
        if (millis() - t0 > 20000) {
            Serial.println("\nWiFi timeout!");
            setUiError("WiFi timeout");
            renderEyes(uiState);
        }
    }
       


    setUiState(UI_IDLE);
    renderEyes(uiState);
    Serial.println("\nWiFi подключён!");
    Serial.print("IP адрес: ");
    Serial.println(WiFi.localIP());

    // Настройка I²S
    setupI2S_Microphone();
    setupI2S_Speaker();

    // Настройка touch
    pinMode(TOUCH_PIN, INPUT);
    Serial.println("Touch sensor initialized on GPIO4 (TTP223)");

    // Тест динамика
    testSpeaker();

    // Запуск задачи для записи и отправки аудио (микрофон → UDP)
    xTaskCreatePinnedToCore(
        audioTask,
        "audioTask",
        4096,
        NULL,
        1,
        &audioTaskHandle,
        1  // Core 1
    );
}

void loop() {
    static int  lastTouchState = LOW;
    int         currentState   = digitalRead(TOUCH_PIN);

    // Обнаружение фронта нажатия (LOW -> HIGH)
    if (lastTouchState == LOW && currentState == HIGH && !isRecording) {
        Serial.println("Нажатие: старт записи");
        isRecording   = true;
        recordStartMs = millis();
        setUiState(UI_RECORDING);
        renderEyes(uiState);
    }

    // Если идёт запись и вышли за пределы RECORD_DURATION_MS — останавливаем
    if (isRecording && (millis() - recordStartMs >= RECORD_DURATION_MS)) {
        Serial.println("Время записи истекло, остановка и запрос воспроизведения");
        isRecording   = false;
        playRequested = true;
        // кратко вернёмся в idle (или можно оставить recording до play)
        setUiState(UI_IDLE);
        renderEyes(uiState);
    }

    lastTouchState = currentState;

    // Если завершили запись — один раз воспроизводим ответ с сервера
    if (playRequested) {
        playRequested = false;  
          // сбрасываем флаг, чтобы не зациклиться
          
        setUiState(UI_PLAYING);
        renderEyes(uiState);
        playAudioOnceFromServer();
        if (uiState != UI_ERROR) {
          setUiState(UI_IDLE);
          renderEyes(uiState);
        }
    }
    static uint32_t lastUi = 0;
    if (millis() - lastUi > 250) {
      lastUi = millis();
      renderEyes(uiState);
    }
    delay(10);  // небольшая задержка, чтобы не крутить цикл слишком быстро
}
