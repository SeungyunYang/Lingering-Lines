/*
 * NeoPixel 감정별 오로라 테스트 (Arduino Nano)
 *
 * 하드웨어 (본 프로젝트 스펙):
 *   - NeoPixel DIN → D7 (데이터선 330Ω, 스트립은 외부 5V 전원)
 *   - GND는 Pi/외부 PSU/Arduino 공통 (5V 레일은 서로 묶지 않음)
 *
 * 테스트 방법:
 *   아래 ACTIVE_EMOTION 값만 0~5 중 하나로 바꾸고 업로드하면,
 *   해당 감정 팔레트 안에서만 오로라처럼 부드럽게 그라데이션 + 천천히 흐름.
 *
 * 의존성: Arduino IDE / arduino-cli 에서 "Adafruit NeoPixel" 라이브러리 설치
 */

#include <Adafruit_NeoPixel.h>

// ---------------------------------------------------------------------------
// ★ 테스트할 감정 하나만 선택 (0 ~ 5). 나머지는 코드에서 사용 안 함.
//    0=JOY  1=SADNESS  2=ANGER  3=FEAR  4=SURPRISE  5=DISGUST
// ---------------------------------------------------------------------------
#define ACTIVE_EMOTION 0

#define NEOPIXEL_PIN 7
#define NUM_PIXELS 12
#define BRIGHTNESS_MAX 40  // 외부 전원 사용 시에도 과전류 방지 (필요 시 20~80 조절)

Adafruit_NeoPixel strip(NUM_PIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);

// 각 감정: 팔레트 3색 (시작 → 중간 → 끝), 스트립 위치로 보간 + 시간으로 흐름
struct Palette3 {
  uint8_t r0, g0, b0;
  uint8_t r1, g1, b1;
  uint8_t r2, g2, b2;
};

static const Palette3 PAL_JOY = {
  255, 230, 80,   // 밝은 노랑
  255, 140, 40,   // 주황
  255, 200, 120,  // 살구/라이트 오렌지
};

static const Palette3 PAL_SADNESS = {
  30, 60, 140,
  80, 120, 200,
  150, 180, 255,
};

static const Palette3 PAL_ANGER = {
  200, 20, 20,
  255, 60, 40,
  120, 0, 0,
};

static const Palette3 PAL_FEAR = {
  80, 40, 120,
  140, 80, 180,
  40, 20, 60,
};

static const Palette3 PAL_SURPRISE = {
  255, 120, 200,
  200, 100, 255,
  255, 200, 255,
};

static const Palette3 PAL_DISGUST = {
  60, 120, 40,
  100, 140, 60,
  40, 80, 30,
};

static const Palette3 *const PALETTES[] = {
  &PAL_JOY,
  &PAL_SADNESS,
  &PAL_ANGER,
  &PAL_FEAR,
  &PAL_SURPRISE,
  &PAL_DISGUST,
};

static void colorAlongStrip(const Palette3 *p, float u, uint8_t *r, uint8_t *g, uint8_t *b) {
  u = constrain(u, 0.0f, 1.0f);
  if (u < 0.5f) {
    float t = u / 0.5f;
    *r = (uint8_t)(p->r0 + (p->r1 - p->r0) * t);
    *g = (uint8_t)(p->g0 + (p->g1 - p->g0) * t);
    *b = (uint8_t)(p->b0 + (p->b1 - p->b0) * t);
  } else {
    float t = (u - 0.5f) / 0.5f;
    *r = (uint8_t)(p->r1 + (p->r2 - p->r1) * t);
    *g = (uint8_t)(p->g1 + (p->g2 - p->g1) * t);
    *b = (uint8_t)(p->b1 + (p->b2 - p->b1) * t);
  }
}

void setup() {
  strip.begin();
  strip.setBrightness(BRIGHTNESS_MAX);
  strip.show();
}

void loop() {
#if ACTIVE_EMOTION < 0 || ACTIVE_EMOTION > 5
#error "ACTIVE_EMOTION must be 0..5"
#endif

  const Palette3 *pal = PALETTES[ACTIVE_EMOTION];
  float phase = millis() * 0.00035f;

  for (uint16_t i = 0; i < NUM_PIXELS; i++) {
    float pos = (float)i / (float)(NUM_PIXELS > 1 ? (NUM_PIXELS - 1) : 1);
    // 오로라: 위치 + 느린 사인으로 팔레트를 따라 흐름
    float u = pos * 0.85f + 0.15f * sin(phase * 6.28318f + pos * 3.5f);
    u = u - floor(u);
    uint8_t r, g, b;
    colorAlongStrip(pal, u, &r, &g, &b);
    strip.setPixelColor(i, r, g, b);
  }

  strip.show();
  delay(16);
}
