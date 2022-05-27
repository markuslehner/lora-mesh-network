#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include "SSD1306Wire.h" 

// I2C pins
#define MPU_SDA 33
#define MPU_SCL 32

Adafruit_MPU6050 mpu;

// display
SSD1306Wire display(0x3c, 4, 15, GEOMETRY_128_64, I2C_TWO);

// Current time
unsigned long currentTime = millis();
// Previous time
unsigned long previousTime = 0; 
// last sensor update
unsigned long lastUpdateTime = 0; 
// update cycle time
const long updateCycle = 500; 

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
    Wire.begin(MPU_SDA, MPU_SCL);

    if (!mpu.begin(MPU6050_I2CADDR_DEFAULT, &Wire, 0)) {
        Serial.println("Sensor init failed");
        while (1)
        yield();
    }
    Serial.println("Found a MPU-6050 sensor");

    Serial.println("MPU6050 Test");
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