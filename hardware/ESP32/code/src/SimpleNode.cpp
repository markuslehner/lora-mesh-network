#include <math.h>

#include <SPI.h>
#include <LoRa.h>
#include <Wire.h> 
#include "SSD1306Wire.h" 

#include <esp_adc_cal.h>
#include <driver/adc.h>

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

// display
SSD1306Wire display(0x3c, 4, 15);
//Adafruit_SSD1306 display(128, 64, &Wire, 16);

int counter = 0;

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
int percent = 0;
//******************************** needed for running average (smoothening the analog value)
const int numReadings = 32;     // the higher the value, the smoother the average
int readings[numReadings];      // the readings from the analog input
int readIndex = 0;              // the index of the current reading
int total = 0;                  // the running total
int average = 0;                // the average

esp_adc_cal_characteristics_t *adc_chars;


//node logic
const char appID[] = "\xca\xfe";
const char data_type = 0x00;
const char node_id = 0x27;

const int SF = 12;
const int CR = 5;
const unsigned long BW = 125000;

const double symbol_duration = 1000.0 / ( double(BW) / (1L << SF) );

void setup() {
    Serial.begin(9600);
    while (!Serial);

    Serial.println("LoRa Sender");

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
}

void loop() {

    digitalWrite(VBATT_GPIO, LOW);              // ESP32 Lora v2.1 reads on GPIO37 when GPIO21 is low
    delay(ADC_READ_STABILIZE);   
    pinMode(ADC1_CHANNEL_1, OPEN_DRAIN);        // ADC GPIO37
    val = adc1_get_raw(ADC1_CHANNEL_1);
    pinMode(ADC1_CHANNEL_1, INPUT);     

    voltage = esp_adc_cal_raw_to_voltage(val, adc_chars);  
    voltage*=VOLTAGE_DIVIDER;               

    percent = 100*(voltage/1000.0-3.0) / 1.2;

    currentTime = millis();

    if (currentTime - lastUpdateTime > updateCycle) {

        lastUpdateTime = millis();

        Serial.print("Sending packet: ");
        Serial.println(counter);

        // send packet
        LoRa.beginPacket();
        size_t byte_cnt = LoRa.print(appID);
        byte_cnt += LoRa.print(data_type);
        byte_cnt += LoRa.print(node_id);
        byte_cnt += LoRa.print("hello ");
        byte_cnt += LoRa.print(counter);
        // measure tx time
        unsigned long tx_start = millis();
        LoRa.endPacket();
        Serial.printf("  Sending took: %lu ms \n",  millis()- tx_start);

        counter++;

        Serial.printf("  Sent %i bytes \n",  byte_cnt);
        double air_time = (12 + 4.25 + 8 + ceil( double(8*byte_cnt - 4*SF + 28)/(4*SF) )*CR )*symbol_duration;
        Serial.printf("  Should have taken %.2f ms \n",  air_time);


        //display stuff
        display.clear();

        // Display static text
        display.drawString(0, 0, "Nr. packets sent: "+ String(counter));

        // display battery level
        display.drawString(0, 15, "Analog read: "+ String(val));
        display.drawString(0, 30, "Voltage: "+ String(voltage));
        display.drawString(0, 45, "Percent: "+ String(percent));

        display.display(); 
    }
}