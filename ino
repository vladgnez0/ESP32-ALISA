#include "Arduino.h"
#include "WiFi.h"
#include "Audio.h"
#include <HTTPClient.h>
#include <ArduinoJson.h>

#define I2S_DOUT     25
#define I2S_BCLK      26
#define I2S_LRC        27

Audio audio;
HTTPClient http;

String ssid = "Arduino";
String password = "12345678";
String address = "http://192.168.137.1:7000";

// Функция для подключения к Wi-Fi
void connectToWiFi() {
  WiFi.disconnect();
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid.c_str(), password.c_str());

  while (WiFi.status() != WL_CONNECTED) {
    delay(1500);
    Serial.println("Connecting to WiFi...");
  }

  Serial.println("WiFi connected");
}

// Функция для отправки POST запроса на сервер и получения ответа
String sendPostRequest(String url, String payload) {
  http.begin(url.c_str());
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(31000); // Timeout 31 секунд

  int httpResponseCode = http.POST(payload);
  if (httpResponseCode > 0) {
    String response = http.getString();
    Serial.println("HTTP Response Code: " + String(httpResponseCode));
    return response;
  } else {
    Serial.println("Error on HTTP request");
    return "";
  }
}

// Функция для формирования JSON запроса
String createJsonRequest() {
  StaticJsonDocument<200> doc;
  doc["inputs"] = "Привет";

  String requestBody;
  serializeJson(doc, requestBody);

  return requestBody;
}

// Функция для подключения и воспроизведения аудио
void playAudioStream(String streamUrl) {
  audio.connecttohost(streamUrl.c_str());

  while (audio.isRunning()) {
    audio.loop();
  }
}

// Основная функция для получения и воспроизведения аудио
void toSound() {
  String fullUrl = address + "/gpt/";
  String requestBody = createJsonRequest();

  String response = sendPostRequest(fullUrl, requestBody);

  if (response.isEmpty()) {
    Serial.println("Empty response from server.");
    return;
  }

  Serial.println("Response: " + response);

  // Подключаемся к аудио потоку
  String audioStreamUrl = address + "/stream";
  playAudioStream(audioStreamUrl);
}

void setup() {
  Serial.begin(115200);

  // Подключаемся к Wi-Fi
  connectToWiFi();

  // Настроим вывод для I2S
  audio.setPinout(I2S_BCLK, I2S_LRC, I2S_DOUT);
  audio.setVolume(20);

  // Получаем и воспроизводим аудио
  toSound();
}

void loop() {
  // В основной loop ничего не нужно делать, так как воспроизведение уже происходит в функции playAudioStream
}
