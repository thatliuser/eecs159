#include <BLEDevice.h>
#include <BLEService.h>
#include <BLEUtils.h>
#include <ICM_20948.h>
#include <esp_timer.h>
#include <string.h>

constexpr const char SERVICE_UUID[] = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
constexpr const char BLINK_UUID[] =
    "11111111-36e1-4688-b7f5-ea07361b26a8";
constexpr const char IMU_UUID[] =
    "22222222-1111-7688-b7f5-ea07361b26a8";

constexpr int BUILTIN_LED = 2;

portMUX_TYPE blinkMtx = portMUX_INITIALIZER_UNLOCKED;
volatile bool blink = true;
bool ledOn = false;
bool paired = false;
bool wasPaired = false;

hw_timer_t *timer = nullptr;
BLEServer *server = nullptr;
BLECharacteristic* getIMU;
ICM_20948_I2C sensor1;
ICM_20948_I2C sensor2;
uint64_t last_read_us = 0;

class ServerNotifs : public BLEServerCallbacks {
  void onConnect(BLEServer *) { paired = true; };

  void onDisconnect(BLEServer *) { paired = false; }
};

class BlinkUpdate : public BLECharacteristicCallbacks {
  void onWrite(BLECharacteristic *c) {
    auto bytes = c->getValue();
    if (bytes.length() == 1) {
      portENTER_CRITICAL(&blinkMtx);
      bool newBlink = static_cast<bool>(bytes[0]);
      if (newBlink != blink) {
        Serial.println("Toggling blink");
      } else {
        Serial.println("Blink set to the same value as before");
      }
      blink = newBlink;
      portEXIT_CRITICAL(&blinkMtx);
    } else {
      Serial.println("Couldn't parse written value, ignored");
    }
  }
  void onRead(BLECharacteristic *c) {
    portENTER_CRITICAL(&blinkMtx);
    uint8_t value = blink;
    c->setValue(&value, 1);
    portEXIT_CRITICAL(&blinkMtx);
  }
};

void notify() {
  sensor1.getAGMT();
  sensor2.getAGMT();
  uint64_t now = static_cast<uint64_t>(esp_timer_get_time());
  uint64_t delta = now - last_read_us;
  uint8_t buf[sizeof(float) * 18 + sizeof(uint64_t)];
  float accX1 = sensor1.accX();
  float accY1 = sensor1.accY();
  float accZ1 = sensor1.accZ();
  float gyrX1 = sensor1.gyrX();
  float gyrY1 = sensor1.gyrY();
  float gyrZ1 = sensor1.gyrZ();
  float magX1 = sensor1.magX();
  float magY1 = sensor1.magY();
  float magZ1 = sensor1.magZ();
  float accX2 = sensor2.accX();
  float accY2 = sensor2.accY();
  float accZ2 = sensor2.accZ();
  float gyrX2 = sensor2.gyrX();
  float gyrY2 = sensor2.gyrY();
  float gyrZ2 = sensor2.gyrZ();
  float magX2 = sensor2.magX();
  float magY2 = sensor2.magY();
  float magZ2 = sensor2.magZ();
  memcpy(buf + sizeof(float) * 0,  &accX1, sizeof(float));
  memcpy(buf + sizeof(float) * 1,  &accY1, sizeof(float));
  memcpy(buf + sizeof(float) * 2,  &accZ1, sizeof(float));
  memcpy(buf + sizeof(float) * 3,  &gyrX1, sizeof(float));
  memcpy(buf + sizeof(float) * 4,  &gyrY1, sizeof(float));
  memcpy(buf + sizeof(float) * 5,  &gyrZ1, sizeof(float));
  memcpy(buf + sizeof(float) * 6,  &magX1, sizeof(float));
  memcpy(buf + sizeof(float) * 7,  &magY1, sizeof(float));
  memcpy(buf + sizeof(float) * 8,  &magZ1, sizeof(float));
  memcpy(buf + sizeof(float) * 9,  &accX2, sizeof(float));
  memcpy(buf + sizeof(float) * 10, &accY2, sizeof(float));
  memcpy(buf + sizeof(float) * 11, &accZ2, sizeof(float));
  memcpy(buf + sizeof(float) * 12, &gyrX2, sizeof(float));
  memcpy(buf + sizeof(float) * 13, &gyrY2, sizeof(float));
  memcpy(buf + sizeof(float) * 14, &gyrZ2, sizeof(float));
  memcpy(buf + sizeof(float) * 15, &magX2, sizeof(float));
  memcpy(buf + sizeof(float) * 16, &magY2, sizeof(float));
  memcpy(buf + sizeof(float) * 17, &magZ2, sizeof(float));
  memcpy(buf + sizeof(float) * 18, &delta, sizeof(uint64_t));
  getIMU->setValue(buf, sizeof(buf));
  getIMU->notify();
  last_read_us = now;
}

void ARDUINO_ISR_ATTR tick() {
  portENTER_CRITICAL_ISR(&blinkMtx);
  if (blink) {
    digitalWrite(BUILTIN_LED, ledOn ? HIGH : LOW);
    ledOn = !ledOn;
  }
  portEXIT_CRITICAL_ISR(&blinkMtx);
}

void setup() {
  // Configure serial and builtin LED
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT);

  Wire.begin();
  // I2C fast mode
  Wire.setClock(400000);

  // ad0 is set to 1 to set the I2C address to 0x69 (compatible with Adafruit board)
  auto status = sensor1.begin(Wire, 1);
  if (status != ICM_20948_Stat_Ok) {
    while (true) {
      Serial.print("Couldn't configure sensor #1: ");
      Serial.println(status);
      delay(1000);
    }
  }
  // ad0 is set to 0 to set the I2C address to 0x68 (second sensor has different addr)
  status = sensor2.begin(Wire, 0);
  if (status != ICM_20948_Stat_Ok) {
    while (true) {
      Serial.print("Couldn't configure sensor #2: ");
      Serial.println(status);
      delay(1000);
    }
  }

  // Configure blink timer
  timer = timerBegin(1000000);
  if (timer == nullptr) {
    Serial.println("Couldn't configure timer!!");
  }
  timerAttachInterrupt(timer, &tick);
  timerAlarm(timer, 1000000, true, 0);

  // Configure bluetooth
  BLEDevice::init("ZotPen");

  server = BLEDevice::createServer();
  server->setCallbacks(new ServerNotifs());

  auto *service = server->createService(SERVICE_UUID);
  // Configure blink characteristic
  auto *setBlink = service->createCharacteristic(
      BLINK_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_WRITE);
  getIMU = service->createCharacteristic(
      IMU_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);

  setBlink->setValue("\0");
  setBlink->setCallbacks(new BlinkUpdate());
  getIMU->setValue("\0");

  service->start();

  auto *adv = server->getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);
  // functions that help with iPhone connections issue
  adv->setMinPreferred(0x06);
  adv->setMinPreferred(0x12);
  adv->start();
}

void loop() {
  delay(50);
  if (sensor1.dataReady() && sensor2.dataReady()) {
    notify();
  }

  // Connecting to device
  if (paired && !wasPaired) {
    wasPaired = true;
  }
  // Disconnecting to device
  if (!paired && wasPaired) {
    wasPaired = false;
    delay(500);
    server->startAdvertising();
    Serial.println("Device unpaired, advertising again");
  }
}
