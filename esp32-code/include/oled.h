#include <Arduino.h>
#include <U8g2lib.h>
#include <SPI.h>
#include <string.h>

// ===== OLED (SPI) pins =====
#define OLED_CS   5
#define OLED_DC   16
#define OLED_RST  17
// SCK=18, MOSI=23 берутся аппаратно (VSPI)

// Если вдруг у тебя SH1106, замени SSD1306 на SH1106 (ниже)
U8G2_SSD1306_128X64_NONAME_F_4W_HW_SPI u8g2(U8G2_R0, /*cs=*/OLED_CS, /*dc=*/OLED_DC, /*reset=*/OLED_RST);
// U8G2_SH1106_128X64_NONAME_F_4W_HW_SPI u8g2(U8G2_R0, /*cs=*/OLED_CS, /*dc=*/OLED_DC, /*reset=*/OLED_RST);

// ===== UI states =====
enum UiState : uint8_t {
  UI_BOOT = 0,
  UI_WIFI_CONNECTING,
  UI_IDLE,
  UI_RECORDING,
  UI_PLAYING,
  UI_ERROR
};

volatile UiState uiState = UI_BOOT;

// текст ошибки (пишем из разных мест)
static char uiError[64] = {0};
static portMUX_TYPE uiMux = portMUX_INITIALIZER_UNLOCKED;

void setUiState(UiState s) {
  uiState = s;
}

void setUiError(const char* msg) {
  portENTER_CRITICAL(&uiMux);
  strncpy(uiError, msg, sizeof(uiError) - 1);
  uiError[sizeof(uiError) - 1] = 0;
  portEXIT_CRITICAL(&uiMux);
  uiState = UI_ERROR;
}

// ===== Eye drawing helpers =====
static void drawEye(int cx, int cy, int r, bool blink, int pupil_dx, int pupil_dy) {
  // контур
  u8g2.drawCircle(cx, cy, r, U8G2_DRAW_ALL);

  if (blink) {
    // "закрытый глаз" — линия
    u8g2.drawLine(cx - r, cy, cx + r, cy);
    return;
  }

  // зрачок
  int pr = max(2, r / 3);
  u8g2.drawDisc(cx + pupil_dx, cy + pupil_dy, pr, U8G2_DRAW_ALL);
}

void renderEyes(UiState s) {
  static uint32_t lastFrameMs = 0;
  static bool blink = false;

  uint32_t now = millis();

  // Мигать раз в ~1.2 сек, закрытие ~120мс
  blink = ((now % 1200) < 120);

  // Если хочешь ограничить FPS (чтобы не грузить), раскомментируй:
  // if (now - lastFrameMs < 120) return; // ~8 FPS
  // lastFrameMs = now;

  u8g2.clearBuffer();
  u8g2.setFont(u8g2_font_6x12_tr);

  const int leftX = 44, rightX = 84, y = 30, r = 12;

  if (s == UI_WIFI_CONNECTING) {
    u8g2.drawStr(0, 12, "WiFi connecting...");
    int dx = (int)((now / 150) % 7) - 3; // -3..+3
    drawEye(leftX,  y, r, blink, dx, 0);
    drawEye(rightX, y, r, blink, dx, 0);
  }
  else if (s == UI_IDLE) {
    u8g2.drawStr(0, 12, "Idle");
    drawEye(leftX,  y, r, blink, 0, 0);
    drawEye(rightX, y, r, blink, 0, 0);
  }
  else if (s == UI_RECORDING) {
    u8g2.drawStr(0, 12, "Recording...");
    // "злые" глазки + "брови"
    drawEye(leftX,  y, r, false, -3, 1);
    drawEye(rightX, y, r, false,  3, 1);
    u8g2.drawLine(leftX  - 10, y - 14, leftX  + 6,  y - 10);
    u8g2.drawLine(rightX - 6,  y - 10, rightX + 10, y - 14);
  }
  else if (s == UI_PLAYING) {
    u8g2.drawStr(0, 12, "Playing...");
    // "радостные" глазки
    u8g2.drawCircle(leftX,  y, r, U8G2_DRAW_ALL);
    u8g2.drawCircle(rightX, y, r, U8G2_DRAW_ALL);
    u8g2.drawDisc(leftX,  y + 2, r/2, U8G2_DRAW_ALL);
    u8g2.drawDisc(rightX, y + 2, r/2, U8G2_DRAW_ALL);

    // УЛЫБКА: без drawArc (чтобы компилилось в любых версиях U8g2)
    u8g2.drawLine(52, 52, 64, 58);
    u8g2.drawLine(64, 58, 76, 52);

    // если хочешь "толще":
    // u8g2.drawLine(52, 53, 64, 59);
    // u8g2.drawLine(64, 59, 76, 53);
  }
  else if (s == UI_ERROR) {
    u8g2.drawStr(0, 12, "ERROR!");
    // крестики вместо глаз
    u8g2.drawLine(leftX  - 8, y - 8, leftX  + 8, y + 8);
    u8g2.drawLine(leftX  + 8, y - 8, leftX  - 8, y + 8);
    u8g2.drawLine(rightX - 8, y - 8, rightX + 8, y + 8);
    u8g2.drawLine(rightX + 8, y - 8, rightX - 8, y + 8);

    // текст ошибки
    char msg[64];
    portENTER_CRITICAL(&uiMux);
    strncpy(msg, uiError, sizeof(msg) - 1);
    msg[sizeof(msg) - 1] = 0;
    portEXIT_CRITICAL(&uiMux);

    // Если сообщение длинное — обрежем
    if (strlen(msg) > 20) msg[20] = 0;

    u8g2.setCursor(0, 54);
    u8g2.print(msg);
  }
  else { // UI_BOOT
    u8g2.drawStr(0, 12, "Boot...");
    drawEye(leftX,  y, r, blink, 0, 0);
    drawEye(rightX, y, r, blink, 0, 0);
  }

  u8g2.sendBuffer();
}
