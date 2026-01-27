// mega_motor_shield_linefollower_serial.ino
// Adafruit Motor Shield v1 (L293D) + 2 IR sensors + Serial control from Raspberry Pi
#include <AFMotor.h>

// IR Sensors
#define LEFT_SENSOR  A0
#define RIGHT_SENSOR A1

// =========================
// Flame + MQ-2 (Analog)
// NOTE: Keep A0/A1 for line sensors. Use A2/A3 for environment sensors.
// =========================
#define MQ2_PIN   A3
#define FLAME_PIN A2

// Tune thresholds (0–1023)
// MQ-2: higher value usually means more gas/smoke
int GAS_BAD_THRESHOLD = 400;
// Flame: many flame sensors give LOWER value when flame is present
int FLAME_DETECT_THRESHOLD = 450;

// MQ-2 warm-up (ms)
const unsigned long MQ2_WARMUP_MS = 20000;
unsigned long warmup_until = 0;

// Sensor report interval (ms)
const unsigned long SENSOR_INTERVAL_MS = 500;
unsigned long last_sensor_send = 0;

// Motors (Adafruit Motor Shield v1)
AF_DCMotor motor1(1, MOTOR12_1KHZ);  // M1 Rear Left
AF_DCMotor motor2(2, MOTOR12_1KHZ);  // M2 Rear Right
AF_DCMotor motor3(3, MOTOR34_1KHZ);  // M3 Front Right
AF_DCMotor motor4(4, MOTOR34_1KHZ);  // M4 Front Left

// Speed
int SPEED = 120;

// Modes
enum Mode { AUTO_LF, MANUAL };
Mode mode = AUTO_LF;

// Serial input buffer
String cmd = "";

void setAllMotorsSpeed(int spd) {
  motor1.setSpeed(spd);
  motor2.setSpeed(spd);
  motor3.setSpeed(spd);
  motor4.setSpeed(spd);
}

void forward() {
  motor1.run(FORWARD);
  motor2.run(FORWARD);
  motor3.run(FORWARD);
  motor4.run(FORWARD);
}

void backward() {
  motor1.run(BACKWARD);
  motor2.run(BACKWARD);
  motor3.run(BACKWARD);
  motor4.run(BACKWARD);
}

void turnLeft() {
  // spin turn (same as your working logic)
  motor1.run(BACKWARD); // Rear Left
  motor4.run(BACKWARD); // Front Left
  motor2.run(FORWARD);  // Rear Right
  motor3.run(FORWARD);  // Front Right
}

void turnRight() {
  motor1.run(FORWARD);  // Rear Left
  motor4.run(FORWARD);  // Front Left
  motor2.run(BACKWARD); // Rear Right
  motor3.run(BACKWARD); // Front Right
}

void stopMotors() {
  motor1.run(RELEASE);
  motor2.run(RELEASE);
  motor3.run(RELEASE);
  motor4.run(RELEASE);
}

void handleAutoLineFollower() {
  int leftVal  = digitalRead(LEFT_SENSOR);
  int rightVal = digitalRead(RIGHT_SENSOR);

  // 0/0 forward, 0/1 right, 1/0 left, 1/1 stop
  if (leftVal == 0 && rightVal == 0) forward();
  else if (leftVal == 0 && rightVal == 1) turnRight();
  else if (leftVal == 1 && rightVal == 0) turnLeft();
  else stopMotors();
}

void applyCommand(String c) {
  c.trim();
  c.toUpperCase();

  if (c == "STOP") {
    stopMotors();
    return;
  }
  if (c == "AUTO_LF") {
    mode = AUTO_LF;
    stopMotors();
    return;
  }
  if (c == "MANUAL") {
    mode = MANUAL;
    stopMotors();
    return;
  }

  // SPEED <0-255>
  if (c.startsWith("SPEED")) {
    int sp = c.substring(5).toInt();
    if (sp < 0) sp = 0;
    if (sp > 255) sp = 255;
    SPEED = sp;
    setAllMotorsSpeed(SPEED);
    return;
  }

  // Movement commands work only in MANUAL
  if (mode != MANUAL) return;

  if (c == "FWD") forward();
  else if (c == "BACK") backward();
  else if (c == "LEFT") turnLeft();
  else if (c == "RIGHT") turnRight();
}

void readSerialLine() {
  while (Serial.available()) {
    char ch = (char)Serial.read();
    if (ch == '\n') {
      applyCommand(cmd);
      cmd = "";
    } else if (ch != '\r') {
      cmd += ch;
      if (cmd.length() > 40) cmd = ""; // safety
    }
  }
}

void setup() {
  pinMode(LEFT_SENSOR, INPUT);
  pinMode(RIGHT_SENSOR, INPUT);
  Serial.begin(9600);

  // MQ-2 needs warm-up time for stable readings
  warmup_until = millis() + MQ2_WARMUP_MS;

  setAllMotorsSpeed(SPEED);
  stopMotors();
}

void sendSensorStatus() {
  int mq2Value = analogRead(MQ2_PIN);
  int flameValue = analogRead(FLAME_PIN);

  bool warming = (millis() < warmup_until);
  bool gasBad = (!warming) && (mq2Value >= GAS_BAD_THRESHOLD);
  bool flameDetected = (flameValue < FLAME_DETECT_THRESHOLD);

  // One line, easy to parse on Raspberry Pi
  // Example:
  // SENSOR FLAME=1 GAS=0 MQ2VAL=356 FLAMEVAL=512 WARM=1
  Serial.print("SENSOR ");
  Serial.print("FLAME="); Serial.print(flameDetected ? 1 : 0);
  Serial.print(" GAS="); Serial.print(gasBad ? 1 : 0);
  Serial.print(" MQ2VAL="); Serial.print(mq2Value);
  Serial.print(" FLAMEVAL="); Serial.print(flameValue);
  Serial.print(" WARM="); Serial.println(warming ? 1 : 0);
}

void loop() {
  readSerialLine();

  if (mode == AUTO_LF) {
    handleAutoLineFollower();
  }

  // periodic sensor publish
  if (millis() - last_sensor_send >= SENSOR_INTERVAL_MS) {
    last_sensor_send = millis();
    sendSensorStatus();
  }

  delay(5); // reduce jitter
}
