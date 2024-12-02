#include <BLEDevice.h>
#include <BLEService.h>
#include <BLEUtils.h>
#include <ICM_20948.h>
#include <esp_timer.h>
#include <string.h>

constexpr const char SERVICE_UUID[] = "4fafc201-1fb5-459e-8fcc-c5c9c331914b";
constexpr const char BLINK_UUID[] =
    "11111111-36e1-4688-b7f5-ea07361b26a8";
constexpr const char ACCEL_UUID[] =
    "acce1e70-1111-7688-b7f5-ea07361b26a8";
constexpr const char GYRO_UUID[] =
    "5c093333-e6e1-4688-b7f5-ea07361b26a8";
constexpr const char MAGNET_UUID[] =
    "aaaaaaaa-aaaa-4688-b7f5-ea07361b26a8";

constexpr int BUILTIN_LED = 2;
constexpr int IMU_INT = 5;

portMUX_TYPE blinkMtx = portMUX_INITIALIZER_UNLOCKED;
portMUX_TYPE notifyMtx = portMUX_INITIALIZER_UNLOCKED;
volatile bool blink = true;
bool ledOn = false;
bool paired = false;
bool wasPaired = false;
volatile bool needNotify = false;

hw_timer_t *timer = nullptr;
BLEServer *server = nullptr;
BLECharacteristic* getAccel;
BLECharacteristic* getGyro;
BLECharacteristic* getMagnet;
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

void setSensorValue(BLECharacteristic* chr, float x, float y, float z) {
  uint64_t now = static_cast<uint64_t>(esp_timer_get_time());
  uint64_t delta = now - last_read_us;
  last_read_us = now;
  uint8_t arr[sizeof(float) * 3 + sizeof(uint64_t)];
  memcpy(arr + sizeof(float) * 0, &x, sizeof(float));
  memcpy(arr + sizeof(float) * 1, &y, sizeof(float));
  memcpy(arr + sizeof(float) * 2, &z, sizeof(float));
  memcpy(arr + sizeof(float) * 3, &delta, sizeof(uint64_t));
  chr->setValue(arr, sizeof(arr));
}

void ARDUINO_ISR_ATTR tick() {
  portENTER_CRITICAL_ISR(&blinkMtx);
  if (blink) {
    digitalWrite(BUILTIN_LED, ledOn ? HIGH : LOW);
    ledOn = !ledOn;
  }
  portEXIT_CRITICAL_ISR(&blinkMtx);
}

void ARDUINO_ISR_ATTR imu_data_ready() {
  Serial.println("I don't know if this works in an ISR but hi");
  sensor.getAGMT();
  setSensorValue(getAccel, sensor.accX(), sensor.accY(), sensor.accZ());
  setSensorValue(getGyro, sensor.gyrX(), sensor.gyrY(), sensor.gyrZ());
  setSensorValue(getMagnet, sensor.magX(), sensor.magY(), sensor.magZ());
  sensor.clearInterrupts();
  portENTER_CRITICAL_ISR(&notifyMtx);
  needNotify = true;
  portEXIT_CRITICAL_ISR(&notifyMtx);
}

void setup() {
  // Configure serial and builtin LED
  Serial.begin(115200);
  pinMode(BUILTIN_LED, OUTPUT);
  // Attach ISR
  pinMode(IMU_INT, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(IMU_INT), imu_data_ready, FALLING);

  Wire.begin();
  // I2C fast mode
  Wire.setClock(400000);

  // ad0 is set to 1 to set the I2C address to 0x69 (compatible with Adafruit board)
  sensor.begin(Wire, 1);
  sensor.swReset();
  if (sensor.status != ICM_20948_Stat_Ok) {
    while (true) {
      Serial.println("Failed to initialize ICM sensor!");
      delay(2000);
    }
  }

  sensor.sleep(false);
  sensor.lowPower(false);
  // TODO: I have no idea what cycled means tbh check datasheet
  sensor.setSampleMode((ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr), ICM_20948_Sample_Mode_Cycled);
  // Config ranges of each sensor
  ICM_20948_smplrt_t sampleRate;
  sampleRate.g = 54;
  sensor.setSampleRate(ICM_20948_Internal_Gyr, sampleRate);
  // Set full scale ranges for both acc and gyr
  ICM_20948_fss_t scale; // This uses a "Full Scale Settings" structure that can contain values for all configurable sensors

  scale.a = gpm2; // (ICM_20948_ACCEL_CONFIG_FS_SEL_e)
                  // gpm2
                  // gpm4
                  // gpm8
                  // gpm16

  scale.g = dps250; // (ICM_20948_GYRO_CONFIG_1_FS_SEL_e)
                    // dps250
                    // dps500
                    // dps1000
                    // dps2000

  sensor.setFullScale((ICM_20948_Internal_Acc | ICM_20948_Internal_Gyr), scale);

  // Interrupt config
  sensor.cfgIntActiveLow(true);
  sensor.cfgIntOpenDrain(false);
  // Interrupt doesn't go away after even is gone - needs to be cleared by MCU
  sensor.cfgIntLatch(true);
  // Pull interrupt pin low when new sensor data is ready
  sensor.intEnableRawDataReady(true);

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
  getMagnet = service->createCharacteristic(
      MAGNET_UUID,
      BLECharacteristic::PROPERTY_READ | BLECharacteristic::PROPERTY_NOTIFY);

  setBlink->setValue("\0");
  setBlink->setCallbacks(new BlinkUpdate());
  getAccel->setValue("\0");
  getGyro->setValue("\0");
  getMagnet->setValue("\0");

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
  delay(5);
  portENTER_CRITICAL(&notifyMtx);
  if (needNotify) {
    // Characteristics were already set in the ISR, just notify
    getAccel->notify();
    getGyro->notify();
    getMagnet->notify();
    needNotify = false;
  }
  portEXIT_CRITICAL(&notifyMtx);

  // Connecting to device
  if (paired && !wasPaired) {
    delay(100);
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
