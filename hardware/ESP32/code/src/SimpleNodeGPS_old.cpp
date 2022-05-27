// #define NO_LORA

#ifndef NO_LORA
    #include <SPI.h>
    #include <LoRa.h>
#endif

#include <math.h>
#include <Wire.h> 
#include "SSD1306Wire.h" 

#include <esp_adc_cal.h>
#include <driver/adc.h>

#include <TinyGPS++.h>
#include <SoftwareSerial.h>

//define LoRa registers
#define REG_PA_CONFIG 0x09
#define REG_PA_DAC 0x4D
#define PA_DAC_HIGH 0x87
#define REG_LNA 0x0c
#define REG_MODEM_CONFIG_1 0x1d
#define REG_MODEM_CONFIG_2 0x1e
#define REG_MODEM_CONFIG_3 0x26
#define REG_OP_MODE 0x01
#define MODE_LONG_RANGE_MODE 0x80
#define MODE_SLEEP 0x00
#define MODE_STDBY 0x01

// define vbettery voltage pin
#define BAT_PIN 37
#define VBATT_GPIO              21      // Heltec GPIO to toggle VBatt read connection ... WARNING!!! This also connects VEXT to VCC=3.3v so be careful what is on header.  Also, take care NOT to have ADC read connection in OPEN DRAIN when GPIO goes HIGH
#define ADC_READ_STABILIZE      5       // in ms (delay from GPIO control and ADC connections times)
#define DEFAULT_VREF            1100    // Default VREF use if no e-fuse calibration
#define VOLTAGE_DIVIDER         3.20    // Lora has 220k/100k voltage divider so need to reverse that reduction via (220k+100k)/100k on vbat GPIO37 or ADC1_1 (early revs were GPIO13 or ADC2_4 but do NOT use with WiFi.begin())

//define the pins used by the transceiver module
#define SS      18
#define RST     14
#define DI0     26

// connection to GPS module
#define RXD2 33
#define TXD2 32
#define GPS_BAUD 9600

//the gps
TinyGPSPlus gps;
//coords of module
double latitude;
double longitude;
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
const long updateCycle = 10000 - 2; // offset to account for internal delay


// battery stuff
// analog read
int val = 0;
// voltage
uint16_t voltage = 0;  
// percentage
uint16_t percent = 0;

esp_adc_cal_characteristics_t *adc_chars;


//node logic
#ifndef NO_LORA
    const char appID[] = "\xca\xfe";
    const char data_type = 0x00;
    const char node_id = 0x00;

    const int SF = 10;
    const int CR = 5;
    const unsigned long BW = 125000;

    const double symbol_duration = 1000.0 / ( double(BW) / (1L << SF) );
#endif

// statistics
int counter = 0;
unsigned long last_send_time = 0;

void setup() {
    Serial.begin(9600);
    while (!Serial);

    Serial.println("LoRa Sender");

    #ifndef NO_LORA
        //setup LoRa transceiver module
        SPI.begin(5, 19, 27, 18);
        LoRa.setPins(SS, RST, DI0);

        if (!LoRa.begin(868E6)) {
            Serial.println("Starting LoRa failed!");
            while (1);
        }

        delay(100);

        // modify LoRa.h to access these private methods
        LoRa.setSpreadingFactor(SF);
        LoRa.setSignalBandwidth(BW);
        LoRa.setPreambleLength(12);
        LoRa.disableCrc();
        LoRa.setCodingRate4(CR);
    #endif

    // reset display
    pinMode(16,OUTPUT); 
    digitalWrite(16, LOW); 
    delay(50); 
    digitalWrite(16, HIGH);
    display.init();

    // battery stuff
    adc_chars = (esp_adc_cal_characteristics_t*)calloc(1, sizeof(esp_adc_cal_characteristics_t));
    // needed for correct read_out even though variable is unused
    esp_adc_cal_value_t val_type = esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_6, ADC_WIDTH_BIT_12, DEFAULT_VREF, adc_chars);
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_1,ADC_ATTEN_DB_6);

    pinMode(VBATT_GPIO, OUTPUT);
    digitalWrite(VBATT_GPIO, LOW);
    delay(ADC_READ_STABILIZE);     

    SerialGPS.begin(GPS_BAUD);

    Serial.println("Started sensor");
}

void loop() {

    while (SerialGPS.available() > 0) {

            int r = SerialGPS.read();
            // Serial.write(r);
            gps.encode(r);
        }

    currentTime = millis();

    if (currentTime - lastUpdateTime > updateCycle) {

        lastUpdateTime = millis();

        // get battery voltage
        digitalWrite(VBATT_GPIO, LOW);              // ESP32 Lora v2.1 reads on GPIO37 when GPIO21 is low
        delay(ADC_READ_STABILIZE);   
        pinMode(ADC1_CHANNEL_1, OPEN_DRAIN);        // ADC GPIO37
        val = adc1_get_raw(ADC1_CHANNEL_1);
        pinMode(ADC1_CHANNEL_1, INPUT);     

        voltage = esp_adc_cal_raw_to_voltage(val, adc_chars);  
        voltage*=VOLTAGE_DIVIDER;               

        percent = 100*(voltage/1000.0-3.0) / 1.2;

         if (gps.location.isValid()) {
            latitude = (gps.location.lat());
            longitude = (gps.location.lng());

            Serial.print("Sending packet: ");
            Serial.println(counter);

            #ifdef NO_LORA
                Serial.println("LoRa disabled");
            #else
                // send packet
                LoRa.beginPacket();
                size_t byte_cnt = LoRa.print(appID);
                size_t test = 0;
                Serial.printf("APP_ID: %i bytes\n", byte_cnt);

                test = LoRa.print(data_type);
                byte_cnt += test;
                Serial.printf("DATA_TYPE: %i bytes\n", test);

                test = LoRa.print(node_id);
                byte_cnt += test;
                Serial.printf("node id: %i bytes\n", test);
                
                test = 0;
                char* p = (char *)(&latitude);
                for (int i = 0; i < 8; ++i)
                {
                    test += LoRa.print(*p);
                    // Serial.printf("%02x", *p);
                    // Serial.printf("%p \n", p);
                    p++;
                }
                Serial.print("\n");
                // test = LoRa.print(reinterpret_cast<char*>(&latitude));
                byte_cnt += test;
                Serial.printf("lat: %i bytes\n", test);

                test = 0;
                p = (char *)(&longitude);
                for (int i = 0; i < 8; ++i)
                {
                    test += LoRa.print(*p);
                    // Serial.printf("%02x", *p);
                    // Serial.printf("%p \n", p);
                    p++;
                }
                Serial.print("\n");
                //test = LoRa.print(reinterpret_cast<char*>(&longitude));
                byte_cnt += test;
                Serial.printf("long: %i bytes\n", test);

                test = 0;
                p = (char *)(&percent);
                for (int i = 0; i < 2; ++i)
                {
                    test += LoRa.print(*p);
                    // Serial.printf("%02x", *p);
                    // Serial.printf("%p \n", p);
                    p++;
                }
                Serial.print("\n");
                byte_cnt += test;
                Serial.printf("battery: %i bytes\n", test);


                // Serial.printf("%p \n", &latitude);
                // Serial.printf("%p \n", &longitude);
                


                // measure tx time
                unsigned long tx_start = millis();
                LoRa.endPacket();
                last_send_time =  millis()- tx_start;
                Serial.printf("  Sending took: %lu ms \n",  last_send_time);

                counter++;

                Serial.printf("  Sent %i bytes \n",  byte_cnt);
                double air_time = (12 + 4.25 + 8 + ceil( double(8*byte_cnt - 4*SF + 28)/(4*SF) )*CR )*symbol_duration;
                Serial.printf("  Should have taken %.2f ms \n",  air_time);
            #endif

        } else {
            Serial.println("No valid GPS data");
        }

        //display stuff
        display.clear();

        char buffer [50];
        sprintf(buffer, "Nr: %i, last time %lu", counter, last_send_time);
        display.drawString(0, 0, buffer);
        sprintf(buffer, "Valid: %i", gps.location.isValid());
        display.drawString(0, 10, buffer);
        // Display gps info
        sprintf(buffer, "num satellites: %i", gps.satellites.value());
        display.drawString(0, 20, buffer);
        sprintf(buffer, "Latitude: %.6f", latitude);
        display.drawString(0, 30, buffer);
        sprintf(buffer, "Longitude: %.6f", longitude);
        display.drawString(0, 40, buffer);
        sprintf(buffer, "Battery: %i", percent);
        display.drawString(0, 50, buffer);

        display.display(); 
    }
}