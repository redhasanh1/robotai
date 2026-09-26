// PINN Humanoid - right hand firmware. ESP32 + PCA9685, protocol v0.1 (see hand/protocol.py).
//
// Wiring (Freenove ESP32):
//   PCA9685 VCC -> 3V3, GND -> GND, SDA -> GPIO21, SCL -> GPIO22, OE -> GPIO25
//   PCA9685 V+ / GND terminal -> 6.0 V supply (NOT the ESP32), 2200 uF cap across it, stripe to GND
//   ESP32 GND and supply GND tied together (common ground)
//   Servo channels: 0 thumb, 1 index, 2 middle, 3 ring, 4 pinky, 5 wrist
//
// Safety, all of it on this chip so a dead laptop or cable cannot hurt the hand:
//   - OE held HIGH at boot: no pulses, servos limp, until the first move command.
//   - Staggered start: channels are switched on one at a time, 150 ms apart (no 6-servo inrush at once).
//   - Clamp: every pulse is clamped to the channel's [min,max] (defaults 1300..1700 us until calibrated).
//   - Slew limit: pulses move toward the target at most W us per second (default 1500 us/s).
//   - Watchdog: after the first command, 200 ms (D command, 100-2000) without a valid line -> outputs off.
//   - BOOT line reports the reset reason; reset=BROWNOUT means the power rail sagged, not a code bug.
//   - E-stop: 'E' turns outputs off until 'R'.
//
// No libraries needed beyond the ESP32 Arduino core (Wire + Preferences).

#include <Wire.h>
#include <Preferences.h>
#include <esp_system.h>

#define FW_VERSION "0.1"
#define NCH 6
#define PCA_ADDR 0x40
#define PIN_OE 25
#define WATCHDOG_DEFAULT_MS 200
#define STAGGER_MS 150
#define TICK_MS 10  // 100 Hz servo update

Preferences prefs;

enum State { IDLE, RUN, ESTOP, WATCHDOG };
const char* STATE_NAME[] = {"IDLE", "RUN", "ESTOP", "WATCHDOG"};
State state = IDLE;

uint16_t lo[NCH], hi[NCH];      // clamp per channel
float cur[NCH];                 // where the slew limiter is now (us); 0 = channel not started
uint16_t target[NCH];           // commanded (clamped) pulse; 0 = never commanded
uint32_t slewUsPerS = 1500;
uint32_t watchdogMs = WATCHDOG_DEFAULT_MS;   // D command; raise it if the real USB link has latency spikes
uint32_t lastRx = 0, lastTick = 0, enableAt[NCH];
bool everCommanded = false;
char line[96];
uint8_t lineLen = 0;

// ---------- PCA9685 ----------
void pcaWrite(uint8_t reg, uint8_t val) {
  Wire.beginTransmission(PCA_ADDR);
  Wire.write(reg);
  Wire.write(val);
  Wire.endTransmission();
}

bool pcaInit() {
  Wire.begin(21, 22);
  Wire.setClock(400000);
  Wire.beginTransmission(PCA_ADDR);
  if (Wire.endTransmission() != 0) return false;
  pcaWrite(0x00, 0x10);            // MODE1: sleep so the prescaler can be written
  pcaWrite(0xFE, 121);             // prescale = round(25 MHz / (4096 * 50 Hz)) - 1 -> 50 Hz
  pcaWrite(0x00, 0x20);            // wake, auto-increment
  delay(1);
  pcaWrite(0x00, 0xA0);            // restart + auto-increment
  pcaWrite(0x01, 0x04);            // MODE2: totem-pole outputs
  return true;
}

void pcaPulse(uint8_t ch, float us) {
  // 50 Hz -> 20000 us per 4096 ticks. us = 0 means full off for that channel.
  uint16_t off = us <= 0 ? 0 : (uint16_t)(us * 4096.0f / 20000.0f + 0.5f);
  Wire.beginTransmission(PCA_ADDR);
  Wire.write(0x06 + 4 * ch);
  Wire.write(0);
  Wire.write(0);
  if (us <= 0) { Wire.write(0); Wire.write(0x10); }   // FULL_OFF bit
  else { Wire.write(off & 0xFF); Wire.write(off >> 8); }
  Wire.endTransmission();
}

void outputs(bool on) { digitalWrite(PIN_OE, on ? LOW : HIGH); }  // OE is active LOW

// ---------- helpers ----------
uint16_t clampUs(uint8_t ch, long us) { return (uint16_t)constrain(us, lo[ch], hi[ch]); }

void loadPrefs() {
  prefs.begin("hand", true);
  for (int i = 0; i < NCH; i++) {
    char k[4];
    snprintf(k, sizeof k, "l%d", i); lo[i] = prefs.getUShort(k, 1300);
    snprintf(k, sizeof k, "h%d", i); hi[i] = prefs.getUShort(k, 1700);
  }
  slewUsPerS = prefs.getUInt("slew", 1500);
  watchdogMs = prefs.getUInt("wd", WATCHDOG_DEFAULT_MS);
  prefs.end();
}

void savePrefs() {
  prefs.begin("hand", false);
  for (int i = 0; i < NCH; i++) {
    char k[4];
    snprintf(k, sizeof k, "l%d", i); prefs.putUShort(k, lo[i]);
    snprintf(k, sizeof k, "h%d", i); prefs.putUShort(k, hi[i]);
  }
  prefs.putUInt("slew", slewUsPerS);
  prefs.putUInt("wd", watchdogMs);
  prefs.end();
}

void stopAll(State why) {
  outputs(false);
  for (int i = 0; i < NCH; i++) { pcaPulse(i, 0); cur[i] = 0; }
  state = why;
}

void startRun() {
  // Channels come back one at a time; each starts AT its target (a servo has no position feedback, so the
  // first pulse is always a jump - staggering keeps it to one servo jumping at a time).
  uint32_t t = millis();
  int k = 0;
  for (int i = 0; i < NCH; i++) enableAt[i] = target[i] ? t + STAGGER_MS * k++ : 0;
  outputs(true);
  state = RUN;
}

void telemetry() {
  Serial.printf("TEL %lu %s", (unsigned long)millis(), STATE_NAME[state]);
  for (int i = 0; i < NCH; i++) Serial.printf(" %d", (int)(cur[i] + 0.5f));
  Serial.print('\n');
}

// ---------- command parser (mirror of hand/protocol.py parse_command) ----------
void handle(char* s) {
  char* tok[8];
  int n = 0;
  for (char* p = strtok(s, " \t\r"); p && n < 8; p = strtok(NULL, " \t\r")) tok[n++] = p;
  if (!n) return;
  long a[7];
  for (int i = 1; i < n; i++) {
    char* end;
    a[i - 1] = strtol(tok[i], &end, 10);
    if (*end) { Serial.println("ERR not a number"); return; }
  }
  char c = tok[0][0];
  int argc = n - 1;
  if (tok[0][1] != 0) { Serial.println("ERR unknown command"); return; }
  lastRx = millis();   // any well-formed line is a heartbeat

  switch (c) {
    case 'V': if (argc) goto badcount; Serial.println("OK V hand-esp32 " FW_VERSION); return;
    case 'H': if (argc) goto badcount; return;
    case 'T': if (argc) goto badcount; telemetry(); return;
    case 'E': if (argc) goto badcount; stopAll(ESTOP); Serial.println("OK E"); return;
    case 'R':
      if (argc) goto badcount;
      if (state == ESTOP || state == WATCHDOG) { startRun(); }
      Serial.println("OK R"); return;
    case 'N': {                           // which hand is this board: N 1 = right, N 2 = left, N = ask
      if (argc > 1) goto badcount;
      if (argc == 1) {
        if (a[0] != 1 && a[0] != 2) { Serial.println("ERR side must be 1 (right) or 2 (left)"); return; }
        prefs.begin("hand", false); prefs.putUChar("side", (uint8_t)a[0]); prefs.end();
      }
      prefs.begin("hand", true); uint8_t side = prefs.getUChar("side", 0); prefs.end();
      Serial.printf("OK N %s\n", side == 1 ? "right" : side == 2 ? "left" : "unset");
      return;
    }
    case 'D':
      if (argc != 1) goto badcount;
      watchdogMs = constrain(a[0], 100, 2000); savePrefs(); Serial.printf("OK D %lu\n", (unsigned long)watchdogMs); return;
    case 'W':
      if (argc != 1) goto badcount;
      slewUsPerS = constrain(a[0], 50, 20000); savePrefs(); Serial.printf("OK W %lu\n", (unsigned long)slewUsPerS); return;
    case 'L':
      if (argc != 3) goto badcount;
      if (a[0] < 0 || a[0] >= NCH || a[1] < 500 || a[2] > 2500 || a[1] >= a[2]) { Serial.println("ERR bad limit"); return; }
      lo[a[0]] = a[1]; hi[a[0]] = a[2]; savePrefs(); Serial.printf("OK L %ld %ld %ld\n", a[0], a[1], a[2]); return;
    case 'S':
      if (argc != 2) goto badcount;
      if (a[0] < 0 || a[0] >= NCH) { Serial.println("ERR bad channel"); return; }
      target[a[0]] = clampUs(a[0], a[1]);
      break;
    case 'M':
      if (argc != NCH) goto badcount;
      for (int i = 0; i < NCH; i++) if (a[i] > 0) target[i] = clampUs(i, a[i]);
      break;
    default: Serial.println("ERR unknown command"); return;
  }
  // S or M
  everCommanded = true;
  if (state == IDLE) startRun();
  if (state == RUN) Serial.println("OK");
  else Serial.printf("ERR %s, send R\n", STATE_NAME[state]);
  return;
badcount:
  Serial.println("ERR wrong argument count");
}

void setup() {
  pinMode(PIN_OE, OUTPUT);
  outputs(false);                       // first thing: no pulses
  Serial.begin(115200);
  loadPrefs();
  for (int i = 0; i < NCH; i++) { cur[i] = 0; target[i] = 0; enableAt[i] = 0; }
  if (!pcaInit()) {
    while (true) { Serial.println("ERR PCA9685 not found at 0x40 - check SDA 21 / SCL 22 / 3V3 / GND"); delay(1000); }
  }
  for (int i = 0; i < NCH; i++) pcaPulse(i, 0);
  // Why did we (re)start? BROWNOUT = the 6 V rail sagged and took the 3.3 V side with it (servos starting
  // together, loose cap) - it looks exactly like a software crash, so say it out loud.
  const char* why[] = {"UNKNOWN", "POWERON", "EXT", "SW", "PANIC", "INT_WDT", "TASK_WDT", "WDT", "DEEPSLEEP",
                       "BROWNOUT", "SDIO"};
  int r = (int)esp_reset_reason();
  Serial.printf("BOOT hand-esp32 " FW_VERSION " reset=%s\n", (r >= 0 && r <= 10) ? why[r] : "OTHER");
}

void loop() {
  while (Serial.available()) {
    char ch = Serial.read();
    if (ch == '\n') { line[lineLen] = 0; handle(line); lineLen = 0; }
    else if (lineLen < sizeof(line) - 1) line[lineLen++] = ch;
    else { lineLen = 0; Serial.println("ERR line too long"); }
  }
  uint32_t now = millis();
  if (state == RUN && everCommanded && now - lastRx > watchdogMs) {
    stopAll(WATCHDOG);
    Serial.printf("ERR WATCHDOG no command for %lu ms, outputs off, send R\n", (unsigned long)watchdogMs);
  }
  if (now - lastTick >= TICK_MS) {
    float step = slewUsPerS * (now - lastTick) / 1000.0f;
    lastTick = now;
    if (state != RUN) return;
    for (int i = 0; i < NCH; i++) {
      if (!target[i] || (enableAt[i] && now < enableAt[i])) continue;
      if (cur[i] == 0) cur[i] = target[i];                       // first pulse for this channel
      else if (cur[i] < target[i]) cur[i] = min(cur[i] + step, (float)target[i]);
      else if (cur[i] > target[i]) cur[i] = max(cur[i] - step, (float)target[i]);
      pcaPulse(i, cur[i]);
    }
  }
}
