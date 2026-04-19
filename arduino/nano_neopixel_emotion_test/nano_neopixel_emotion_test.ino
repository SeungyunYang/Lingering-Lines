/*
 * NeoPixel 감정 테스트 — 6개씩 한 그룹, 그룹 안에서만 그라데이션 + 숨쉬기
 *
 * - 스트립을 GROUP_SIZE(기본 6)개 픽셀마다 한 묶음으로 나눔.
 * - 각 묶음은 (시작색 → 끝색)만 사용; 같은 감정 톤 안에서만 조합.
 * - "숨쉬기": 그룹 내부 보간만 살짝 움직임 (millis). 스트립 전체를 따라 불이 흘러가지는 효과 없음.
 *
 * NUM_PIXELS 는 GROUP_SIZE 의 배수여야 함 (예: 36 = 6×6그룹).
 *
 * (예비) LOVE 감정용 팔레트는 파일 내 LOVE_SEGS_RESERVED 로 보관함. 매핑 추가 시 사용.
 */

#include <Adafruit_NeoPixel.h>

// ---------------------------------------------------------------------------
// 테스트할 감정 번호 (아래 숫자↔감정 표기는 유지보수용 — 절대 삭제·축약하지 말 것)
//   0 = JOY (기쁨)
//   1 = SADNESS (슬픔)
//   2 = ANGER (분노)
//   3 = FEAR (두려움)
//   4 = SURPRISE (놀람)
//   5 = DISGUST (혐오)
#define ACTIVE_EMOTION 0

#define NEOPIXEL_PIN 7
#define NUM_PIXELS 36
#define GROUP_SIZE 6
#define BRIGHTNESS_MAX 50

// 그룹 내부만 움직임 (스트립 전체 주행 아님) — 조금 더 다이나믹하게
#define BREATH_SPEED 0.0021f       // 클수록 호흡 빠름 (기존 대비 ~3배)
#define BREATH_AMP 0.50f           // 메인 물결 진폭
#define BREATH_SHIMMER_AMP 0.14f   // 빠른 잔물결 (같은 그룹 안에서만)
#define BREATH_SHIMMER_MULT 2.55f  // 메인보다 빠른 주파수 배율

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

// ---- JOY: 노랑·주황·연두빛 노랑 (채도 살짝↑ — B 낮추고 R/G 대비 유지) ----------
// SegGrad: rs, gs, bs, re, ge, be (Arduino AVR는 중첩 {{}} 초기화에 실패할 수 있음)
static const SegGrad JOY_SEGS[NUM_GROUPS] = {
    {255, 212, 12, 255, 98, 8},    // 선명 노랑 → 주황
    {255, 98, 8, 255, 212, 18},    // 주황 → 노랑
    {200, 242, 42, 255, 212, 18},  // 연두빛 노랑 → 레몬
    {255, 212, 18, 208, 252, 58},  // 레몬 → 라임
    {255, 92, 6, 215, 245, 52},    // 주황 → 연두
    {255, 198, 14, 255, 128, 12},  // 밝은 노랑 → 앰버
};

// ---- SADNESS: 파랑 베이스 유지 + 홀수 그룹(1,3,5)은 보랏빛 강하게 ----------------
// 짝수(0,2,4)=청·하늘·오션 블루 / 홀수(1,3,5)=퍼리윙클·라벤더·인디고 퍼플
static const SegGrad SADNESS_SEGS[NUM_GROUPS] = {
    {22, 72, 168, 125, 200, 255},    // [파랑] 딥 아쿠아 → 밝은 하늘
    {52, 42, 132, 182, 172, 255},    // [보라↑] 인디고 블루 → 퍼리윙클
    {32, 98, 215, 158, 215, 255},    // [파랑] 선명 블루 → 아이스 블루
    {165, 155, 252, 38, 42, 118},    // [보라↑] 라벤더 화이트 → 딥 바이올렛
    {26, 92, 198, 108, 192, 250},    // [파랑] 오션 → 지평선 블루
    {72, 62, 178, 202, 188, 255},    // [보라↑] 블루바이올렛 → 소프트 라벤더
};

// ---- LOVE (예비): 6감정 인덱스에는 없음 — 나중에 LOVE 추가 시 이 SegGrad 사용. 삭제 금지 ----
// 핑크·코랄·따뜻한 레드 (연애 느낌). ACTIVE_EMOTION 과 연결하지 않음; 통합 시 EMOTION_SEGS 에 매핑.
static const SegGrad LOVE_SEGS_RESERVED[NUM_GROUPS] __attribute__((unused)) = {
    {255, 22, 18, 255, 95, 8},      // 스칼렛 → 선명 주황
    {255, 48, 95, 190, 12, 22},     // 핫 핑크 → 크림슨
    {255, 105, 12, 255, 125, 118},  // 탠저린 → 코랄 핑크
    {195, 14, 20, 255, 78, 18},     // 딥 레드 → 플레임 오렌지
    {255, 35, 88, 255, 100, 28},    // 마젠타 핑크 → 네온 오렌지
    {255, 88, 105, 175, 8, 18},     // 연핑크·살몬 → 블러드 레드
};

// ---- ANGER: 고채도 빨강·붉은 주황 (G를 낮춰 노란빛·골든 느낌 억제) ----------------
static const SegGrad ANGER_SEGS[NUM_GROUPS] = {
    {255, 10, 7, 255, 58, 0},       // 스칼렛 → 레드오렌지 (G≤60대)
    {205, 3, 4, 250, 52, 0},        // 블러드 → 불꽃 (노랗지 않게)
    {255, 20, 8, 255, 65, 0},       // 밝은 레드 → 오렌지레드
    {185, 3, 5, 255, 55, 0},        // 다크 레드 → 탠저린(붉은 기)
    {255, 32, 10, 255, 68, 0},      // 화염 레드 → 선명 주황 (골든 아님)
    {220, 6, 5, 248, 48, 2},        // 크림슨 → 녹슨 오렌지
};

// ---- FEAR: 짙은 보라 + [보라↑] 고채도 구간 / [회색] 탈채도 구간 번갈아 ----------
static const SegGrad FEAR_SEGS[NUM_GROUPS] = {
    {95, 38, 175, 175, 85, 235},     // [보라↑] 바이올렛 → 선명 퍼플
    {105, 103, 115, 82, 80, 92},     // [회색] 쿨 그레이 → 딥 그레이
    {125, 48, 195, 58, 32, 118},     // [보라↑] 밝은 퍼플 → 인디고
    {118, 116, 128, 92, 90, 102},    // [회색] 연한 스틸 → 차가운 회색
    {72, 35, 165, 195, 95, 245},     // [보라↑] 딥 퍼플 → 일렉트릭 바이올렛
    {98, 96, 108, 72, 70, 88},       // [회색] 블루그레이 → 거의 검은 회색
};

// ---- SURPRISE: 다이나믹 핑크·마젠타·푸시아 (구간마다 명암·채도 대비 크게) -----
static const SegGrad SURPRISE_SEGS[NUM_GROUPS] = {
    {165, 12, 95, 255, 45, 210},     // 딥 마젠타 → 네온 핫핑크 번쩍
    {255, 35, 175, 255, 145, 235},   // 선명 푸시아 → 버블검 플래시
    {95, 8, 72, 255, 65, 225},       // 어두운 로즈 → 일렉트릭 핑크
    {255, 55, 195, 210, 25, 145},    // 밝은 핑크 → 풍선 마젠타
    {200, 20, 140, 255, 110, 245},   // 라즈베리 → 형광 핑크
    {240, 40, 185, 255, 165, 250},   // 미디엄 푸시아 → 코튼캔디 하이라이트
};

// ---- DISGUST (V1 백업): 이전에 마음에 들었던 톤 — 되돌리려면 DISGUST_SEGS 를 이 값으로 교체. 삭제 금지
static const SegGrad DISGUST_SEGS_V1_BACKUP[NUM_GROUPS] __attribute__((unused)) = {
    {70, 115, 45, 110, 145, 65},
    {100, 135, 55, 55, 95, 40},
    {85, 125, 50, 120, 150, 70},
    {60, 105, 42, 95, 130, 58},
    {115, 140, 62, 75, 110, 48},
    {90, 128, 52, 105, 138, 60},
};

// ---- DISGUST: 올리브·역녹 (채도↑, B는 G보다 낮게 유지 — 푸른빛·틸 방지) ----------
static const SegGrad DISGUST_SEGS[NUM_GROUPS] = {
    {88, 118, 28, 118, 132, 42},     // 선명 올리브 → 밝은 역록
    {105, 108, 26, 62, 88, 24},      // 탁한 페어 그린 → 짙은 이끼
    {75, 115, 30, 112, 122, 38},     // 늪 녹 → 흙기 도는 녹
    {115, 110, 32, 72, 82, 26},      // 카키 → 썩은 진녹
    {95, 122, 34, 125, 128, 44},     // 먼지 연록(채도↑) → 마른 잎
    {65, 108, 26, 102, 115, 36},     // 군록 → 어두운 올리브
};

static const SegGrad *const EMOTION_SEGS[6] = {
    JOY_SEGS,
    SADNESS_SEGS,
    ANGER_SEGS,
    FEAR_SEGS,
    SURPRISE_SEGS,
    DISGUST_SEGS,
};

void setup() {
  strip.begin();
  strip.setBrightness(BRIGHTNESS_MAX);
  strip.show();
}

void loop() {
#if ACTIVE_EMOTION < 0 || ACTIVE_EMOTION > 5
#error "ACTIVE_EMOTION must be 0..5"
#endif

  const SegGrad *segs = EMOTION_SEGS[ACTIVE_EMOTION];
  float t = (float)millis() * BREATH_SPEED;

  for (uint16_t i = 0; i < NUM_PIXELS; i++) {
    uint8_t g = (uint8_t)(i / GROUP_SIZE);
    uint8_t local = (uint8_t)(i % GROUP_SIZE);
    float u = (GROUP_SIZE <= 1) ? 0.0f : (float)local / (float)(GROUP_SIZE - 1);

    // 느린 호흡 + 빠른 시머(그룹·픽셀 위상만, 스트립 길이로는 이동 안 함)
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
