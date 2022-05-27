#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include "SSD1306Wire.h" 

// I2C pins
#define MPU_SDA 33
#define MPU_SCL 32

#define RTC_PRESENT

Adafruit_MPU6050 mpu;
// if RTC DS3231 has same addr 0x68 as MPU6050, so pull AD0 a MPU high to change address to 0x69
#ifdef RTC_PRESENT
    #define MPU_ADDR 0x69
    #include "RTClib.h"
    RTC_DS3231 rtc;
#else
    #define MPU_ADDR MPU6050_I2CADDR_DEFAULT
#endif

// display
SSD1306Wire display(0x3c, 4, 15, GEOMETRY_128_64, I2C_TWO);

// Current time
unsigned long currentTime = millis();
// Previous time
unsigned long previousTime = 0; 
// last sensor update
unsigned long lastUpdateTime = 0; 
// update cycle time
const long updateCycle = 10000; 

RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR unsigned long millisOffset=0;

unsigned long get_time_since_start()
{
    return millis() + millisOffset;
}

void sleepSensor(unsigned long sleepMillis)
{
    esp_sleep_enable_timer_wakeup(sleepMillis * 1000);
    millisOffset = get_time_since_start() + sleepMillis;
    esp_deep_sleep_start();
}

void setup() {
    // Start the Serial Monitor
    Serial.begin(9600);

    // reset display
    pinMode(16,OUTPUT); 
    digitalWrite(16, LOW); 
    delay(50); 
    digitalWrite(16, HIGH);

    display.init();
    // Show initial display buffer contents on the screen --
    // the library initializes this with an Adafruit splash screen.
    display.clear();


    // MPU6050
    #ifndef NO_SENSOR
        // MPU6050
        Wire.begin(MPU_SDA, MPU_SCL);

        if (!mpu.begin(MPU_ADDR, &Wire, 0)) {
            Serial.println("Sensor init failed");
            while (1)
            yield();
        }
        Serial.println("Found a MPU-6050 sensor");
        Serial.println("Started node!");
    #endif

    //Increment boot number and print it every reboot
    ++bootCount;
    Serial.println("Boot number: " + String(bootCount));

    /*
    First we configure the wake up source
    We set our ESP32 to wake up every 5 seconds
    */
    esp_sleep_enable_timer_wakeup(5 * 1000000);

    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    char buffer [50];
    sprintf(buffer, "Temperature: %.2f", temp.temperature);
    display.drawString(0, 0, buffer);
    display.display();

    delay(500);


    Serial.printf("Going to sleep @ %lu", get_time_since_start());
    sleepSensor(5000);
}

void loop() {

    currentTime = millis();

    if (currentTime - lastUpdateTime > updateCycle) {

        lastUpdateTime = currentTime;

        sensors_event_t a, g, temp;
        mpu.getEvent(&a, &g, &temp);

        Serial.print("\t\tTemperature ");
        Serial.print(temp.temperature);
        Serial.println(" deg C");

        Serial.print("Accelerometer ");
        Serial.print("X: ");
        Serial.print(a.acceleration.x, 2);
        Serial.print(" m/s^2, ");
        Serial.print("Y: ");
        Serial.print(a.acceleration.y, 2);
        Serial.print(" m/s^2, ");
        Serial.print("Z: ");
        Serial.print(a.acceleration.z, 2);
        Serial.println(" m/s^2");

        //display stuff
        display.clear();

        
        char buffer [50];
        sprintf(buffer, "Temperature: %.2f", temp.temperature);
        display.drawString(0, 0, buffer);

        sprintf(buffer, "ACC-X: %.2f", a.acceleration.x);
        display.drawString(0, 10, buffer);

        sprintf(buffer, "ACC-Y: %.2f", a.acceleration.y);
        display.drawString(0, 20, buffer);

        sprintf(buffer, "ACC-Z: %.2f", a.acceleration.z);
        display.drawString(0, 30, buffer);

        display.display(); 
    }
}