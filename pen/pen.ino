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
ICM_20948_I2C sensor;
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
  sensor.getAGMT();
  uint64_t now = static_cast<uint64_t>(esp_timer_get_time());
  uint64_t delta = now - last_read_us;
  uint8_t buf[sizeof(float) * 9 + sizeof(uint64_t)];
  float accX = sensor.accX();
  float accY = sensor.accY();
  float accZ = sensor.accZ();
  float gyrX = sensor.gyrX();
  float gyrY = sensor.gyrY();
  float gyrZ = sensor.gyrZ();
  float magX = sensor.magX();
  float magY = sensor.magY();
  float magZ = sensor.magZ();
  memcpy(buf + sizeof(float) * 0, &accX, sizeof(float));
  memcpy(buf + sizeof(float) * 1, &accY, sizeof(float));
  memcpy(buf + sizeof(float) * 2, &accZ, sizeof(float));
  memcpy(buf + sizeof(float) * 3, &gyrX, sizeof(float));
  memcpy(buf + sizeof(float) * 4, &gyrY, sizeof(float));
  memcpy(buf + sizeof(float) * 5, &gyrZ, sizeof(float));
  memcpy(buf + sizeof(float) * 6, &magX, sizeof(float));
  memcpy(buf + sizeof(float) * 7, &magY, sizeof(float));
  memcpy(buf + sizeof(float) * 8, &magZ, sizeof(float));
  memcpy(buf + sizeof(float) * 9, &delta, sizeof(uint64_t));
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
  sensor.begin(Wire, 1);

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
  if (sensor.dataReady()) {
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
