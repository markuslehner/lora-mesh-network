#include <SPI.h>
#include <Wire.h> 
#include "SSD1306Wire.h" 

#include <esp_adc_cal.h>
#include <driver/adc.h>

// define vbettery voltage pin
#define BAT_PIN 37
#define VBATT_GPIO              21      // Heltec GPIO to toggle VBatt read connection ... WARNING!!! This also connects VEXT to VCC=3.3v so be careful what is on header.  Also, take care NOT to have ADC read connection in OPEN DRAIN when GPIO goes HIGH
#define ADC_READ_STABILIZE      5       // in ms (delay from GPIO control and ADC connections times)
#define DEFAULT_VREF            1100    // Default VREF use if no e-fuse calibration
#define VOLTAGE_DIVIDER         3.20    // Lora has 220k/100k voltage divider so need to reverse that reduction via (220k+100k)/100k on vbat GPIO37 or ADC1_1 (early revs were GPIO13 or ADC2_4 but do NOT use with WiFi.begin())


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
const long updateCycle = 10000 ; // offset to account for internal delay


// battery stuff
// analog read
int val = 0;
// voltage
uint16_t voltage = 0;  
// percentage
int percent = 0;

esp_adc_cal_characteristics_t *adc_chars;


void setup() {
    Serial.begin(9600);
    while (!Serial);

    Serial.println("Battery Test");

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

    currentTime = millis();

    if (currentTime - lastUpdateTime > updateCycle) {

        lastUpdateTime = millis();

        digitalWrite(VBATT_GPIO, LOW);              // ESP32 Lora v2.1 reads on GPIO37 when GPIO21 is low
        delay(ADC_READ_STABILIZE);   
        pinMode(ADC1_CHANNEL_1, OPEN_DRAIN);        // ADC GPIO37
        val = adc1_get_raw(ADC1_CHANNEL_1);
        pinMode(ADC1_CHANNEL_1, INPUT);     

        voltage = esp_adc_cal_raw_to_voltage(val, adc_chars);  
        voltage*=VOLTAGE_DIVIDER;               

        percent = 100*(voltage/1000.0-3.0) / 1.2;

        //display stuff
        display.clear();

        // Display static text
        display.drawString(0, 0, "Battery test");

        // display battery level
        display.drawString(0, 15, "Analog read: "+ String(val));
        display.drawString(0, 30, "Voltage: "+ String(voltage));
        display.drawString(0, 45, "Percent: "+ String(percent));

        display.display(); 
    }
}
