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

// own library
#include <Packet.h>
#include <PacketHandler.h>

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
const long updateCycle = 5000 - 2; // offset to account for internal delay
// last time display was updated
unsigned long last_display_update_time = 100; 
// update cycle time
unsigned long display_update_interval = 100 - 1; // offset to account for internal delay
// current time
unsigned long current_time;

// battery stuff
// analog read
int val = 0;
// voltage
uint16_t voltage = 0;  
// percentage
uint16_t percent = 0;

esp_adc_cal_characteristics_t *adc_chars;
esp_adc_cal_value_t val_type;

//node logic
#ifndef NO_LORA
    const unsigned char appID[2] {0xaf, 0xfe};
    const char data_type = 0x00;
    const char node_id = 177;

    const int SF = 7;
    const int CR = 5;
    const unsigned long BW = 125000;
    const int tx_power = 14;
    const double symbol_duration = 1000.0 / ( double(BW) / (1L << SF) );
#endif

// statistics
unsigned char send_cnt = 0;
int rec_cnt = 0;
unsigned long last_send_time = 0;

// forward declaration of methods
Packet create_data_packet();
Packet create_empty_packet();
void receive_packet();
void update_display();

void setup() {
    Serial.begin(9600);
    while (!Serial);

    Serial.println("LoRa Node:");
    Serial.printf("  ID: %i\n", (unsigned int) node_id);
    Serial.printf("  APP_ID: %i\n", appID[0]*256 + appID[1]);
    Serial.printf("  SF: %i\n", (unsigned int) SF);
    Serial.printf("  BW: %lu\n", BW);
    Serial.printf("  CR: %i\n", (unsigned int) CR);
    Serial.printf("  TX: %i dB\n", (unsigned int) tx_power);

    #ifndef NO_LORA
        //setup LoRa transceiver module
        SPI.begin(5, 19, 27, 18);
        LoRa.setPins(SS, RST, DI0);

        if (!LoRa.begin(868E6)) {
            Serial.println("ERROR: Starting LoRa failed!");
            while (1);
        }

        delay(100);

        // modify LoRa.h to access these private methods
        LoRa.setSpreadingFactor(SF);
        LoRa.setSignalBandwidth(BW);
        LoRa.setPreambleLength(12);
        LoRa.disableCrc();
        LoRa.setCodingRate4(CR);
        LoRa.setTxPower(tx_power);
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
    val_type = esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_6, ADC_WIDTH_BIT_12, DEFAULT_VREF, adc_chars);
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_1,ADC_ATTEN_DB_6);

    pinMode(VBATT_GPIO, OUTPUT);
    digitalWrite(VBATT_GPIO, LOW);
    delay(ADC_READ_STABILIZE);     

    SerialGPS.begin(GPS_BAUD);

    Serial.println("Started node!");
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
            Serial.println(send_cnt);

            #ifdef NO_LORA
                Serial.println("LoRa disabled");
            #else
                // test new way
                Packet p = create_data_packet();

                char data_buffer[50];
                p.to_bytes(appID, data_buffer);
                LoRa.beginPacket();
                size_t byte_cnt = 0;
                for (int i = 0; i < p.get_length(); i++) {
                    // Serial.printf("%02x", data_buffer[i]);
                    byte_cnt += LoRa.print(data_buffer[i]);
                }
                // Serial.println();

                // measure tx time
                unsigned long tx_start = millis();
                LoRa.endPacket();
                last_send_time =  millis()- tx_start;
                Serial.printf("  Sending took: %lu ms \n",  last_send_time);

                send_cnt++;

                Serial.printf("  Sent %i bytes \n",  byte_cnt);
                double air_time = (12 + 4.25 + 8 + ceil( double(8*byte_cnt - 4*SF + 28)/(4*SF) )*CR )*symbol_duration;
                Serial.printf("  Should have taken %.2f ms \n",  air_time);

            #endif
        }
    }

    // update display
    current_time = millis();
    if (current_time - last_display_update_time > display_update_interval) {

        last_display_update_time = current_time;
        update_display();
    }

    int packetSize = LoRa.parsePacket();
    if (packetSize) {
        receive_packet();
    }
 
}  

void update_display() {
    //display stuff
    display.clear();
    current_time = millis();

    char buffer [50];
    sprintf(buffer, "sent: %i, last time %lu", send_cnt, last_send_time);
    display.drawString(0, 0, buffer);
    sprintf(buffer, "Battery: %i", percent);
    display.drawString(0, 50, buffer);

    // Display gps info
    sprintf(buffer, "Valid: %i", gps.location.isValid());
    display.drawString(0, 10, buffer);
    sprintf(buffer, "TTS: %.1f s", (updateCycle - (current_time - lastUpdateTime))/1000.0 );
    display.drawString(40, 10, buffer);
    sprintf(buffer, "num satellites: %i", gps.satellites.value());
    display.drawString(0, 20, buffer);
    sprintf(buffer, "Latitude: %.6f", latitude);
    display.drawString(0, 30, buffer);
    sprintf(buffer, "Longitude: %.6f", longitude);
    display.drawString(0, 40, buffer);

    display.display(); 
}

void receive_packet() {
    // received a packet
    Serial.println("Received packet with RSSI: ");
    Serial.println(LoRa.packetRssi());

    // read packet
    unsigned char rec_buffer[20];
    int byte_cnt = 0;
    while (LoRa.available()) {
        rec_buffer[byte_cnt] = (unsigned char)LoRa.read();
        //Serial.print(rec_buffer[byte_cnt]);
        byte_cnt++;
    }  

    if(appID[0] == rec_buffer[0] && appID[1] == rec_buffer[1]) {
        Serial.println("Packet was from same network!");
        for(int i = 0; i < byte_cnt; i++) {
            Serial.printf("%02x", rec_buffer[i]);
        }
        Serial.println();

        // decoding
        Serial.printf("Sender: %i\n", rec_buffer[2]);
        Serial.printf("Origin: %i\n", rec_buffer[3]);
        Serial.printf("Target: %i\n", rec_buffer[4]);
        Serial.printf("Hops: %u / %u\n", rec_buffer[5]&15, rec_buffer[5]>>4);
        Serial.printf("Packet-ID: %i\n", rec_buffer[6]);
        Serial.printf("Dir: %i, last_dist: %i\n", rec_buffer[7]>>7, rec_buffer[7]&127);
        Serial.printf("PL-Type: %i\n", rec_buffer[8]);

    }     

    rec_cnt++;
}

Packet create_data_packet() {

    unsigned char payload[20];

    memcpy(payload, (char *)(&latitude), sizeof(latitude));
    memcpy(payload + sizeof(longitude), (char *)(&longitude), sizeof(latitude));
    memcpy(payload + sizeof(longitude) + sizeof(latitude), (char *)(&percent), sizeof(percent));
    size_t payload_length = sizeof(longitude) + sizeof(latitude) + sizeof(percent);

    Serial.printf("payload length: %i bytes\n", payload_length);
    return Packet((unsigned char) 0, node_id, node_id, send_cnt, (unsigned char) 7, 10, true, data_type, payload_length, payload);
}

Packet create_empty_packet() {
    return Packet(node_id, node_id, (unsigned char) 0, send_cnt, (unsigned char) 7, 10, true, data_type, 0, nullptr);
}