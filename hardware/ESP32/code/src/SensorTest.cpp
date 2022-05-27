#include <OneWire.h>
#include <DallasTemperature.h>

// Pin where the DS18B20 is connected to
#define DS18_PIN 32
#define DS18_PWR 33

// Setup a oneWire instance to communicate with any OneWire devices
OneWire oneWire(DS18_PIN);

// Pass our oneWire reference to Dallas Temperature sensor 
DallasTemperature sensors(&oneWire);

// Current time
unsigned long currentTime = millis();
// Previous time
unsigned long previousTime = 0; 
// last sensor update
unsigned long lastUpdateTime = 0; 
// update cycle time
const long updateCycle = 5000; 

void setup() {
    // Start the Serial Monitor
    Serial.begin(9600);

    //power sensor
    pinMode(DS18_PWR, OUTPUT);
    digitalWrite(DS18_PWR, HIGH);
    delay(100);

    Serial.println("start sensor");
    // Start the DS18B20 sensor
    sensors.begin();

    Serial.println("Temperature Test");
}

void loop() {

    currentTime = millis();

    if (currentTime - lastUpdateTime > updateCycle) {

        lastUpdateTime = currentTime;

        sensors.requestTemperatures(); 

        char charBuf[10];
        dtostrf(sensors.getTempCByIndex(0), 7, 2, charBuf);

        Serial.print("Temperature: ");
        Serial.println(charBuf);
    
    }
}