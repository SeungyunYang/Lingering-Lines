#include <string.h>
#include <stdlib.h>
#include <Wire.h>
#include <Adafruit_DRV2605.h>

/*
 * 부스 네비게이션 — 키보드 스위치 → 라즈베리파이 시리얼, NeoPixel 은 Pi 명령으로만 재생
 *
 * 핀 (INPUT_PULLUP, 누름 = LOW):
 *   D2 = Back    D3 = OK(확인/Select)    D5 = Next
 *
 * DRV2605L (I2C, 기본 주소 0x5A):
 *   SDA → A4    SCL → A5    VCC 3.3~5V / GND 공통
 *   코인 햅틱 → DRV OUT+/OUT- (보드 설명서대로). 라이브러리: Adafruit DRV2605 + BusIO
 *   ROM 라이브러리 1 + ERM 가정. 진동이 약하면 useLRA() 로 바꿔 시험.
 *
 * Pi → 보드 (115200, 줄 단위):
 *   PLAY:RANDOM     — 7감정 중 하나 랜덤, 15초간 숨쉬기 후 소등
 *   PLAY:<0-6>      — 해당 감정 15초 재생 후 소등
 *
 * NeoPixel 재생 중: DRV2605 ROM 웨이폼 HAPTIC_WAVEFORM 번호를 재생 끝날 때마다 반복(GO=0 일 때 재트리거)
 *
 * 보드 → Pi:
 *   BTN:BACK / BTN:OK / BTN:NEXT  — 스위치 에지(쿨다운 220ms)
 */

#include <Adafruit_NeoPixel.h>

// TI ROM Library 1 기준 웨이폼 번호(데이터시트 11.2). 사용자 요청: 88
#define HAPTIC_WAVEFORM 88
#define DRV2605_REG_GO 0x0C

#define BTN_BACK 2
#define BTN_OK 3
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
#define NEO_PLAY_MS 15000U

#if (NUM_PIXELS % GROUP_SIZE) != 0
#error "NUM_PIXELS must be a multiple of GROUP_SIZE"
#endif

#define NUM_GROUPS (NUM_PIXELS / GROUP_SIZE)

Adafruit_NeoPixel strip(NUM_PIXELS, NEOPIXEL_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_DRV2605 drv;
static bool drv2605Ok = false;

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

static const SegGrad LOVE_SEGS[NUM_GROUPS] = {
    {255, 22, 18, 255, 95, 8},
    {255, 48, 95, 190, 12, 22},
    {255, 105, 12, 255, 125, 118},
    {195, 14, 20, 255, 78, 18},
    {255, 35, 88, 255, 100, 28},
    {255, 88, 105, 175, 8, 18},
};

static const SegGrad DISGUST_SEGS[NUM_GROUPS] = {
    {88, 118, 28, 118, 132, 42},
    {105, 108, 26, 62, 88, 24},
    {75, 115, 30, 112, 122, 38},
    {115, 110, 32, 72, 82, 26},
    {95, 122, 34, 125, 128, 44},
    {65, 108, 26, 102, 115, 36},
};

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

static bool neoPlaying = false;
static uint32_t neoEndMs = 0;
static uint8_t neoEmotion = 0;

static char rxBuf[40];
static uint8_t rxLen = 0;

static bool readPressed(uint8_t pin) {
  return digitalRead(pin) == LOW;
}

static void drawNeoFrame(uint8_t emo) {
  const SegGrad *segs = EMOTION_SEGS[emo];
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
}

static void hapticStop(void) {
  if (!drv2605Ok) {
    return;
  }
  drv.stop();
}

/** 슬롯 0에만 넣고 나머지는 0으로 두어 시퀀스가 여기서 끝나게 함. go() 전에 stop()으로 큐 리셋. */
static void hapticTriggerEffect(uint8_t effectId) {
  if (!drv2605Ok) {
    return;
  }
  drv.stop();
  drv.setWaveform(0, effectId);
  drv.setWaveform(1, 0);
  for (uint8_t slot = 2; slot < 8; slot++) {
    drv.setWaveform(slot, 0);
  }
  drv.go();
}

static void hapticTriggerWave88(void) {
  hapticTriggerEffect(HAPTIC_WAVEFORM);
}

/** 재생이 끝나면 GO 비트가 0 → 그때마다 같은 웨이폼을 다시 재생(네오 구간과 동기) */
static void hapticLoopWhileNeo(void) {
  if (!drv2605Ok) {
    return;
  }
  uint8_t go = drv.readRegister8(DRV2605_REG_GO);
  if ((go & 0x01) == 0) {
    hapticTriggerWave88();
  }
}

static void stopNeo() {
  neoPlaying = false;
  hapticStop();
  for (uint16_t i = 0; i < NUM_PIXELS; i++) {
    strip.setPixelColor(i, 0, 0, 0);
  }
  strip.show();
}

static void startNeo(uint8_t emo) {
  neoEmotion = emo;
  neoPlaying = true;
  neoEndMs = millis() + NEO_PLAY_MS;
  hapticTriggerWave88();
}

static void processLine(const char *line) {
  /* 하드웨어 확인: 짧은 클릭(1)과 ROM 웨이폼 88 각각 한 번 재생. 코인 모터가 LRA면 useLRA()+selectLibrary(6) 필요 */
  if (strncmp(line, "TEST:HAPTIC", 12) == 0) {
    if (drv2605Ok) {
      hapticTriggerEffect(1);
      delay(400);
      hapticTriggerEffect(HAPTIC_WAVEFORM);
    }
    return;
  }
  if (strncmp(line, "PLAY:RANDOM", 11) == 0) {
    // Pi 에서 PLAY:<0-6> 권장. RANDOM 은 부팅 시 한 번만 씨드된 AVR random 이라 치우칠 수 있어 매번 재시드.
    randomSeed(millis() ^ micros() ^ (uint32_t)analogRead(A0));
    long r = random(0, 7);
    startNeo((uint8_t)r);
    return;
  }
  if (strncmp(line, "PLAY:", 5) == 0) {
    int v = atoi(line + 5);
    if (v >= 0 && v <= 6) {
      startNeo((uint8_t)v);
    }
  }
}

static void pollSerial() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\r') {
      continue;
    }
    if (c == '\n') {
      rxBuf[rxLen] = '\0';
      if (rxLen > 0) {
        processLine(rxBuf);
      }
      rxLen = 0;
      continue;
    }
    if (rxLen < sizeof(rxBuf) - 1) {
      rxBuf[rxLen++] = c;
    } else {
      rxLen = 0;
    }
  }
}

void setup() {
  Serial.begin(115200);
  randomSeed(analogRead(A0) ^ (analogRead(A1) << 2) ^ (uint16_t)millis());

  pinMode(BTN_BACK, INPUT_PULLUP);
  pinMode(BTN_OK, INPUT_PULLUP);
  pinMode(BTN_NEXT, INPUT_PULLUP);

  Wire.begin();
  drv2605Ok = drv.begin();
  if (drv2605Ok) {
    drv.selectLibrary(1);
    drv.useERM();
  }
  Serial.print(F("DRV2605 "));
  Serial.println(drv2605Ok ? F("OK") : F("FAIL (I2C/배선 확인: A4=SDA A5=SCL GND 0x5A)"));

  strip.begin();
  strip.setBrightness(BRIGHTNESS_MAX);
  strip.clear();
  strip.show();
}

void loop() {
  pollSerial();

  static bool prevBack = false;
  static bool prevOk = false;
  static bool prevNext = false;
  static unsigned long lastBtnMs = 0;

  unsigned long now = millis();
  bool canBtn = (now - lastBtnMs) >= BTN_COOLDOWN_MS;

  bool bBack = readPressed(BTN_BACK);
  bool bOk = readPressed(BTN_OK);
  bool bNext = readPressed(BTN_NEXT);

  if (canBtn) {
    if (bBack && !prevBack) {
      lastBtnMs = now;
      Serial.println(F("BTN:BACK"));
    } else if (bOk && !prevOk) {
      lastBtnMs = now;
      Serial.println(F("BTN:OK"));
    } else if (bNext && !prevNext) {
      lastBtnMs = now;
      Serial.println(F("BTN:NEXT"));
    }
  }

  prevBack = bBack;
  prevOk = bOk;
  prevNext = bNext;

  if (neoPlaying) {
    if (now >= neoEndMs) {
      stopNeo();
    } else {
      drawNeoFrame(neoEmotion);
      hapticLoopWhileNeo();
      delay(16);
      return;
    }
  }

  delay(4);
}
