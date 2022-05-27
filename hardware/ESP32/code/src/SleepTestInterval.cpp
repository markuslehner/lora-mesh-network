#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>
#include "SSD1306Wire.h" 
#include <esp_adc_cal.h>
#include <driver/adc.h>
#include <iostream>

// I2C pins
#define MPU_SDA 33
#define MPU_SCL 32

// define vbettery voltage pin
#define BAT_PIN 37
#define VBATT_GPIO              21      // Heltec GPIO to toggle VBatt read connection ... WARNING!!! This also connects VEXT to VCC=3.3v so be careful what is on header.  Also, take care NOT to have ADC read connection in OPEN DRAIN when GPIO goes HIGH
#define ADC_READ_STABILIZE      5       // in ms (delay from GPIO control and ADC connections times)
#define DEFAULT_VREF            1100    // Default VREF use if no e-fuse calibration
#define VOLTAGE_DIVIDER         3.20    // Lora has 220k/100k voltage divider so need to reverse that reduction via (220k+100k)/100k on vbat GPIO37 or ADC1_1 (early revs were GPIO13 or ADC2_4 but do NOT use with WiFi.begin())

#define START_TIME 60000
#define ACTIVE_TIME 7500

void update_display();
void get_battery_voltage();

Adafruit_MPU6050 mpu;

//#define RTC_PRESENT
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

// battery stuff
// analog read
int val = 0;
// voltage
uint16_t voltage = 0;  
// percentage
char percent = 0;

RTC_DATA_ATTR esp_adc_cal_characteristics_t *adc_chars;
RTC_DATA_ATTR esp_adc_cal_value_t val_type;

// Current time
RTC_DATA_ATTR long current_time;
// last interval start
RTC_DATA_ATTR long last_interval = 0; 
// interval_length
RTC_DATA_ATTR long send_interval = START_TIME; 
// interval_length
RTC_DATA_ATTR long interval_active_time = ACTIVE_TIME; 
// last send interval
RTC_DATA_ATTR long last_send_time = 2500; 
// next sleep time
RTC_DATA_ATTR long next_sleep_interval = START_TIME + ACTIVE_TIME; 

RTC_DATA_ATTR unsigned long next_wakeup;
RTC_DATA_ATTR unsigned long sleep_time;

RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR unsigned long millisOffset = START_TIME;

// last time display was updated
unsigned long last_display_update_time = 0; 
// update cycle time
unsigned long display_update_interval = 100 - 1; // offset to account for internal delay

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
    Wire.begin(MPU_SDA, MPU_SCL);

    if (!mpu.begin(MPU_ADDR, &Wire, 0)) {
        Serial.println("Sensor init failed");
        while (1)
        yield();
    }
    Serial.println("Found a MPU-6050 sensor");

     // battery stuff
    adc_chars = (esp_adc_cal_characteristics_t*)calloc(1, sizeof(esp_adc_cal_characteristics_t));
    // needed for correct read_out even though variable is unused
    val_type = esp_adc_cal_characterize(ADC_UNIT_1, ADC_ATTEN_DB_6, ADC_WIDTH_BIT_12, DEFAULT_VREF, adc_chars);
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_1,ADC_ATTEN_DB_6);

    pinMode(VBATT_GPIO, OUTPUT);
    digitalWrite(VBATT_GPIO, LOW);
    delay(ADC_READ_STABILIZE);     



    //Increment boot number and print it every reboot
    ++bootCount;
    Serial.println("Boot number: " + String(bootCount));
}

void loop() {

    // update display
    current_time = get_time_since_start();
    if (current_time - last_display_update_time > display_update_interval) {

        last_display_update_time = get_time_since_start();
        update_display();
    }

    if (current_time - last_interval > send_interval) {

        last_interval += send_interval;
        std::cout << "INTERVAL START" << std::endl;
    }

    if (current_time - last_send_time > send_interval) {

            last_send_time += send_interval;

            std::cout << "current_time  " << +current_time << std::endl;
            std::cout << "last_send_time  " << +last_send_time << std::endl;

            get_battery_voltage();
            std::cout << "SENDING..." << std::endl;
        }

    if ( next_sleep_interval < current_time) {

        std::cout << "INTERVAL ACTIVE END" << std::endl;

        std::cout << "next_sleep_interval  " << +next_sleep_interval << std::endl;
        std::cout << "get_time_since_start  " << +get_time_since_start() << std::endl;
        std::cout << "send_interval  " << +send_interval << std::endl;
        std::cout << "interval_active_time  " << +interval_active_time << std::endl;
        std::cout << "current_time  " << +current_time << std::endl;
        std::cout << "last_send_time  " << +last_send_time << std::endl;

        sleep_time = next_sleep_interval - get_time_since_start() + send_interval - interval_active_time - 500;
        next_sleep_interval += send_interval;
        next_wakeup = sleep_time + get_time_since_start();
        std::cout << "SLEEPING FOR: " << +sleep_time<< std::endl;
        sleepSensor(sleep_time);
    }
}

void update_display() {

    // display stuff
    display.clear();
    display.displayOn();

    char buffer [50];
    // line 2
    sprintf(buffer, "TTS: %.1f s", (send_interval - (current_time - last_send_time))/1000.0 );
    display.drawString(0, 20, buffer);
    sprintf(buffer, "INT: %.1f s", (send_interval - (current_time - last_interval))/1000.0 );
    display.drawString(65, 20, buffer);
    // line 3
    sprintf(buffer, "SLP: %.1f s", (next_sleep_interval - current_time)/1000.0 );
    display.drawString(0, 30, buffer);
    sprintf(buffer, "ACT: %.1f s", (interval_active_time)/1000.0 );
    display.drawString(65, 30, buffer);

    //line 5
    sprintf(buffer, "Battery:%i", percent);
    display.drawString(0, 50, buffer);

    display.display(); 
}

void get_battery_voltage() {
    // get battery voltage
    digitalWrite(VBATT_GPIO, LOW);              // ESP32 Lora v2.1 reads on GPIO37 when GPIO21 is low
    delay(ADC_READ_STABILIZE);   
    pinMode(ADC1_CHANNEL_1, OPEN_DRAIN);        // ADC GPIO37
    val = adc1_get_raw(ADC1_CHANNEL_1);
    pinMode(ADC1_CHANNEL_1, INPUT);     

    voltage = esp_adc_cal_raw_to_voltage(val, adc_chars);  
    voltage*=VOLTAGE_DIVIDER;               

    percent = 100*(voltage/1000.0-3.0) / 1.2;
}