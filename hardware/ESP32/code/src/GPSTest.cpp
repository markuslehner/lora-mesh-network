#include <TinyGPS++.h>
#include <SoftwareSerial.h>
#include <Wire.h> 
#include "SSD1306Wire.h" 

// Pin where the DS18B20 is connected to
#define RXD2 33
#define TXD2 32
#define GPS_BAUD 9600

//the gps
TinyGPSPlus gps;
//coords of module
double latitude, longitude;
// The serial connection to the GPS device
SoftwareSerial SerialGPS(RXD2, TXD2); 

// display
SSD1306Wire display(0x3c, 4, 15);
//Adafruit_SSD1306 display(128, 64, &Wire, 16);

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

    Serial.println("GPS TEST");

    // reset display
    pinMode(16,OUTPUT); 
    digitalWrite(16, LOW); 
    delay(50); 
    digitalWrite(16, HIGH);

    display.init();
    // Show initial display buffer contents on the screen --
    // the library initializes this with an Adafruit splash screen.
    display.clear();

    SerialGPS.begin(GPS_BAUD);

    Serial.println("Started sensor");
}

void loop() {

    currentTime = millis();

    while (SerialGPS.available() > 0) {

        int r = SerialGPS.read();
        // Serial.write(r);
        gps.encode(r);
    }

    if (currentTime - lastUpdateTime > updateCycle) {

        lastUpdateTime = currentTime;

        if (gps.location.isValid()) {
            latitude = (gps.location.lat());
            longitude = (gps.location.lng());
        }

        Serial.println("Valid: ");
        Serial.println(gps.location.isValid()); 

        Serial.print("num satellites: ");
        Serial.println(gps.satellites.value()); 

        Serial.printf("Latitude: %.6f \n", latitude);

        Serial.printf("Longitude: %.6f \n", longitude);     

        //display stuff
        display.clear();

        char buffer [50];
        sprintf(buffer, "Valid: %i", gps.location.isValid());
        display.drawString(0, 0, buffer);
        // Display gps info
        sprintf(buffer, "num satellites: %i", gps.satellites.value());
        display.drawString(0, 15, buffer);
        sprintf(buffer, "Latitude: %.6f", latitude);
        display.drawString(0, 30, buffer);
        sprintf(buffer, "Longitude: %.6f", longitude);
        display.drawString(0, 45, buffer);

        display.display(); 
    }
}