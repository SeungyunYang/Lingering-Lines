/*
 * NeoPixel + 키보드 스위치 테스트
 *
 * - Back(D2) / Next(D5): 0~6 감정 라이트 효과 순환 (이전 / 다음)
 * - Select(D3): 전체 NeoPixel 끄기 ↔ 켜기 토글 (켜져 있을 때만 색 표시)
 *
 * INPUT_PULLUP — 누름 = LOW. 팔레트는 nano_neopixel_emotion_test.ino 와 맞춰 두었음(동기화 유지).
 *
 * 감정 번호 (절대 삭제·축약하지 말 것):
 *   0 = JOY  1 = SADNESS  2 = ANGER  3 = FEAR  4 = LOVE  5 = DISGUST  6 = NEUTRAL
 *
 * USB 시리얼(115200): 라즈베리파이가 읽어 e-ink 에 표시
 *   EMO:<0-6>  — 감정 변경 시
 *   LED:<0|1> — Select 로 전체 끔(0) / 켬(1) 시
 */

#include <Adafruit_NeoPixel.h>

#define BTN_BACK 2
#define BTN_SELECT 3
#define BTN_NEXT 5

#define NEOPIXEL_PIN 7
#define NUM_PIXELS 36
#define GROUP_SIZE 6
#define BRIGHTNESS_MAX 50

#define BREATH_SPEED 0.0021f
#define BREATH_AMP 0.50f
#define BREATH_SHIMMER_AMP 0.14f
#define BREATH_SHIMMER_MULT 2.55f

#define BTN_COOLDOWN_MS 220U

// USB→라즈베리 수신 경로 확인용. 1로 두고 업로드하면 loop()에서 주기적으로 LINK:줄을 보냄.
// Pi에서 바이트가 전혀 안 보일 때(충전 전용 케이블·다른 tty·펌웨어 미적용) 구분에 사용. 확인 후 0으로 되돌릴 것.
#define SERIAL_LINK_TEST 0

#if (NUM_PIXELS % GROUP_SIZE) != 0
#error "NUM_PIXELS must be a multiple of GROUP_SIZE"
#endif

#define NUM_GROUPS (NUM_PIXELS / GROUP_SIZE)

Adafruit_NeoPixel strip(NUM_PIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

typedef struct {
  uint8_t rs, gs, bs;
  uint8_t re, ge, be;
} SegGrad;

static void lerpRgb(const SegGrad *sg, float t, uint8_t *r, uint8_t *g, uint8_t *b) {
  if (t < 0.0f) {
    t = 0.0f;
  }
  if (t > 1.0f) {
    t = 1.0f;
  }
  *r = (uint8_t)((float)sg->rs + ((float)sg->re - (float)sg->rs) * t);
  *g = (uint8_t)((float)sg->gs + ((float)sg->ge - (float)sg->gs) * t);
  *b = (uint8_t)((float)sg->bs + ((float)sg->be - (float)sg->bs) * t);
}

// ---- 팔레트 (nano_neopixel_emotion_test.ino 와 동일하게 유지) ----------------
static const SegGrad JOY_SEGS[NUM_GROUPS] = {
    {255, 212, 12, 255, 98, 8},
    {255, 98, 8, 255, 212, 18},
    {200, 242, 42, 255, 212, 18},
    {255, 212, 18, 208, 252, 58},
    {255, 92, 6, 215, 245, 52},
    {255, 198, 14, 255, 128, 12},
};

static const SegGrad SADNESS_SEGS[NUM_GROUPS] = {
    {22, 72, 168, 125, 200, 255},
    {52, 42, 132, 182, 172, 255},
    {32, 98, 215, 158, 215, 255},
    {165, 155, 252, 38, 42, 118},
    {26, 92, 198, 108, 192, 250},
    {72, 62, 178, 202, 188, 255},
};

static const SegGrad LOVE_SEGS[NUM_GROUPS] = {
    {255, 22, 18, 255, 95, 8},
    {255, 48, 95, 190, 12, 22},
    {255, 105, 12, 255, 125, 118},
    {195, 14, 20, 255, 78, 18},
    {255, 35, 88, 255, 100, 28},
    {255, 88, 105, 175, 8, 18},
};

static const SegGrad ANGER_SEGS[NUM_GROUPS] = {
    {255, 10, 7, 255, 58, 0},
    {205, 3, 4, 250, 52, 0},
    {255, 20, 8, 255, 65, 0},
    {185, 3, 5, 255, 55, 0},
    {255, 32, 10, 255, 68, 0},
    {220, 6, 5, 248, 48, 2},
};

static const SegGrad FEAR_SEGS[NUM_GROUPS] = {
    {95, 38, 175, 175, 85, 235},
    {105, 103, 115, 82, 80, 92},
    {125, 48, 195, 58, 32, 118},
    {118, 116, 128, 92, 90, 102},
    {72, 35, 165, 195, 95, 245},
    {98, 96, 108, 72, 70, 88},
};

// (백업) 예전 SURPRISE 팔레트 — 7감정 매핑에서는 미사용. 삭제 금지.
static const SegGrad SURPRISE_SEGS_BACKUP[NUM_GROUPS] __attribute__((unused)) = {
    {165, 12, 95, 255, 45, 210},
    {255, 35, 175, 255, 145, 235},
    {95, 8, 72, 255, 65, 225},
    {255, 55, 195, 210, 25, 145},
    {200, 20, 140, 255, 110, 245},
    {240, 40, 185, 255, 165, 250},
};

static const SegGrad DISGUST_SEGS_V1_BACKUP[NUM_GROUPS] __attribute__((unused)) = {
    {70, 115, 45, 110, 145, 65},
    {100, 135, 55, 55, 95, 40},
    {85, 125, 50, 120, 150, 70},
    {60, 105, 42, 95, 130, 58},
    {115, 140, 62, 75, 110, 48},
    {90, 128, 52, 105, 138, 60},
};

static const SegGrad DISGUST_SEGS[NUM_GROUPS] = {
    {88, 118, 28, 118, 132, 42},
    {105, 108, 26, 62, 88, 24},
    {75, 115, 30, 112, 122, 38},
    {115, 110, 32, 72, 82, 26},
    {95, 122, 34, 125, 128, 44},
    {65, 108, 26, 102, 115, 36},
};

// NEUTRAL: 차분한 웜그레이·실버 (채도 낮음, 중립 톤)
static const SegGrad NEUTRAL_SEGS[NUM_GROUPS] = {
    {188, 188, 192, 155, 155, 162},
    {175, 178, 185, 148, 150, 158},
    {200, 196, 200, 168, 165, 172},
    {165, 168, 175, 135, 138, 145},
    {195, 192, 198, 160, 158, 168},
    {178, 180, 186, 152, 150, 158},
};

static const SegGrad *const EMOTION_SEGS[7] = {
    JOY_SEGS,
    SADNESS_SEGS,
    ANGER_SEGS,
    FEAR_SEGS,
    LOVE_SEGS,
    DISGUST_SEGS,
    NEUTRAL_SEGS,
};

static uint8_t currentEmotion = 0;
static bool lightsOn = true;

static bool readPressed(uint8_t pin) {
  return digitalRead(pin) == LOW;
}

static void emitSerialState() {
  Serial.print(F("EMO:"));
  Serial.println(currentEmotion);
  Serial.print(F("LED:"));
  Serial.println(lightsOn ? 1 : 0);
}

void setup() {
  Serial.begin(115200);
  pinMode(BTN_BACK, INPUT_PULLUP);
  pinMode(BTN_SELECT, INPUT_PULLUP);
  pinMode(BTN_NEXT, INPUT_PULLUP);

  strip.begin();
  strip.setBrightness(BRIGHTNESS_MAX);
  strip.clear();
  strip.show();

  delay(80);
  emitSerialState();
}

void loop() {
  static bool prevBack = false;
  static bool prevSel = false;
  static bool prevNext = false;
  static unsigned long lastBtnMs = 0;

#if SERIAL_LINK_TEST
  static unsigned long lastLinkMs = 0;
  {
    unsigned long t = millis();
    if (t - lastLinkMs >= 4000UL) {
      lastLinkMs = t;
      Serial.println(F("LINK:OK"));
    }
  }
#endif

  unsigned long now = millis();
  bool canAct = (now - lastBtnMs) >= BTN_COOLDOWN_MS;

  bool bBack = readPressed(BTN_BACK);
  bool bSel = readPressed(BTN_SELECT);
  bool bNext = readPressed(BTN_NEXT);

  if (canAct) {
    if (bBack && !prevBack) {
      currentEmotion = (uint8_t)((currentEmotion + 6) % 7);
      lastBtnMs = now;
      Serial.print(F("EMO:"));
      Serial.println(currentEmotion);
    } else if (bNext && !prevNext) {
      currentEmotion = (uint8_t)((currentEmotion + 1) % 7);
      lastBtnMs = now;
      Serial.print(F("EMO:"));
      Serial.println(currentEmotion);
    } else if (bSel && !prevSel) {
      lightsOn = !lightsOn;
      lastBtnMs = now;
      Serial.print(F("LED:"));
      Serial.println(lightsOn ? 1 : 0);
    }
  }

  prevBack = bBack;
  prevSel = bSel;
  prevNext = bNext;

  if (!lightsOn) {
    for (uint16_t i = 0; i < NUM_PIXELS; i++) {
      strip.setPixelColor(i, 0, 0, 0);
    }
    strip.show();
    delay(16);
    return;
  }

  const SegGrad *segs = EMOTION_SEGS[currentEmotion];
  float t = (float)millis() * BREATH_SPEED;

  for (uint16_t i = 0; i < NUM_PIXELS; i++) {
    uint8_t g = (uint8_t)(i / GROUP_SIZE);
    uint8_t local = (uint8_t)(i % GROUP_SIZE);
    float u = (GROUP_SIZE <= 1) ? 0.0f : (float)local / (float)(GROUP_SIZE - 1);

    float breath = BREATH_AMP * sin(t + (float)g * 0.85f);
    breath += BREATH_SHIMMER_AMP * sin(t * BREATH_SHIMMER_MULT + (float)g * 1.15f + (float)local * 0.65f);
    float uu = u + breath;
    if (uu < 0.0f) {
      uu = 0.0f;
    }
    if (uu > 1.0f) {
      uu = 1.0f;
    }

    uint8_t r, gc, b;
    lerpRgb(&segs[g], uu, &r, &gc, &b);
    strip.setPixelColor(i, r, gc, b);
  }

  strip.show();
  delay(16);
}
