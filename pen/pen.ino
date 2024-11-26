#include <BLEDevice.h>
#include <BLEService.h>
#include <BLEUtils.h>
#include <Adafruit_ICM20X.h>
#include <Adafruit_ICM20948.h>
#include <Adafruit_Sensor.h>
#include <string.h>

constexpr const char SERVICE_UUID[] = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
constexpr const char BLINK_UUID[] =
    "11111111-36e1-4688-b7f5-ea07361b26a8";
constexpr const char ACCEL_UUID[] =
    "acce1e70-1111-7688-b7f5-ea07361b26a8";
constexpr const char GYRO_UUID[] =
    "5c093333-e6e1-4688-b7f5-ea07361b26a8";

constexpr int BUILTIN_LED = 2;

portMUX_TYPE blinkMtx = portMUX_INITIALIZER_UNLOCKED;
bool blink = true;
bool ledOn = false;
bool paired = false;
bool wasPaired = false;

hw_timer_t *timer = nullptr;
BLEServer *server = nullptr;
Adafruit_ICM20948 sensor;

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

void ARDUINO_ISR_ATTR tick() {
  portENTER_CRITICAL_ISR(&blinkMtx);
  if (blink) {
    digitalWrite(BUILTIN_LED, ledOn ? HIGH : LOW);
    ledOn = !ledOn;
  }
  portEXIT_CRITICAL_ISR(&blinkMtx);
}

BLECharacteristic* getAccel;
BLECharacteristic* getGyro;

void setup() {
  // Configure serial and builtin LED
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT);

  if (!sensor.begin_I2C()) {
    while (true) {
      Serial.println("Failed to initialize ICM sensor!");
      delay(2000);
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
  getAccel = service->createCharacteristic(
      ACCEL_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);
  getGyro = service->createCharacteristic(
      GYRO_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);

  setBlink->setValue("\0");
  setBlink->setCallbacks(new BlinkUpdate());
  getAccel->setValue("\0");
  getGyro->setValue("\0");

  service->start();

  auto *adv = server->getAdvertising();
  adv->addServiceUUID(SERVICE_UUID);
  adv->setScanResponse(true);
  // functions that help with iPhone connections issue
  adv->setMinPreferred(0x06);
  adv->setMinPreferred(0x12);
  adv->start();
}

void setSensorValue(BLECharacteristic* chr, sensors_vec_t& vec) {
  uint8_t arr[sizeof(float) * 3];
  memcpy(arr + sizeof(float) * 0, &vec.x, sizeof(float));
  memcpy(arr + sizeof(float) * 1, &vec.y, sizeof(float));
  memcpy(arr + sizeof(float) * 2, &vec.z, sizeof(float));
  chr->setValue(arr, sizeof(arr));
}

void loop() {
  delay(100);

  // Read sensors
  sensors_event_t accel;
  sensors_event_t gyro;
  sensors_event_t temp;
  sensor.getEvent(&accel, &gyro, &temp);
  setSensorValue(getAccel, accel.acceleration);
  getAccel->notify();
  setSensorValue(getGyro, gyro.gyro);
  getGyro->notify();

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