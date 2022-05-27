// #define NO_LORA

#ifndef NO_LORA
    #include <SPI.h>
    #include <LoRa.h>
#endif

#include <math.h>
#include <list>
#include <algorithm>

#include <Wire.h> 
#include "SSD1306Wire.h" 

#include <esp_adc_cal.h>
#include <driver/adc.h>

#include <PacketHandler.h>
#include <Node.h>

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

// time 
#define START_TIME 60000

// display
SSD1306Wire display(0x3c, 4, 15, GEOMETRY_128_64, I2C_TWO);

// battery stuff
// analog read
int val = 0;
// voltage
uint16_t voltage = 0;  
// percentage
char percent = 0;

esp_adc_cal_characteristics_t *adc_chars;
esp_adc_cal_value_t val_type;

const unsigned char app_id[2] {0xaf, 0xfe};
const char node_id = 11;

//node logic
#ifndef NO_LORA
    const int SF = 7;
    const int CR = 5;
    const unsigned long BW = 125000;
    const int tx_power = 14;
    const double frequency = 865E6;
    const double symbol_duration = 1000.0 / ( double(BW) / (1L << SF) );
#endif

// UPDATE PARAMS
// current time
unsigned long current_time;
// last time display was updated
unsigned long last_display_update_time = START_TIME; 
// update cycle time
unsigned long display_update_interval = 100 - 1; // offset to account for internal delay
// last time a join request was sent
unsigned long last_join_time = START_TIME + 2000; 
// update cycle time
unsigned long join_retry_interval = 15000 - 2; // offset to account for internal dela


// statistics
RTC_DATA_ATTR int send_cnt = 0;
RTC_DATA_ATTR int rec_cnt = 0;

// sleep
RTC_DATA_ATTR unsigned long millisOffset = START_TIME;

void update_display();
void get_battery_voltage();
unsigned long get_time_since_start();

void setup() {
    Serial.begin(9600);
    while (!Serial);

    Serial.println("LoRa Node:");
    Serial.printf("  APP_ID: %i\n", app_id[0]*256 + app_id[1]);
    Serial.printf("  SF: %i\n", (unsigned int) SF);
    Serial.printf("  BW: %lu\n", BW);
    Serial.printf("  CR: %i\n", (unsigned int) CR);
    Serial.printf("  TX: %i dB\n", (unsigned int) tx_power);

    #ifndef NO_LORA
        //setup LoRa transceiver module
        SPI.begin(5, 19, 27, 18);
        LoRa.setPins(SS, RST, DI0);

        if (!LoRa.begin(frequency)) {
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

    get_battery_voltage();
}

void loop() {

    current_time = get_time_since_start();
    // sending
    if (current_time - last_send_time > send_interval) {

        last_send_time += send_interval;

        get_battery_voltage();

        Serial.print("Sending packet: ");
        Serial.println(send_cnt);

        send_data_packet();
    }

    // update display
    if (current_time - last_display_update_time > display_update_interval) {

        last_display_update_time = current_time;
        update_display();
    }
}

Packet create_data_packet() {

    float temperature = 0;
    float acc_x = 0;
    float acc_y = 0;
    float acc_z = 0;

    unsigned char payload[40];

    memcpy(payload, (char *)(&temperature), sizeof(temperature));
    memcpy(payload + sizeof(temperature), (char *)(&acc_x), sizeof(acc_x));
    memcpy(payload + sizeof(temperature) + sizeof(acc_x), (char *)(&acc_y), sizeof(acc_y));
    memcpy(payload + sizeof(temperature) + sizeof(acc_x) + sizeof(acc_y), (char *)(&acc_z), sizeof(acc_z));
    memcpy(payload + sizeof(temperature) + sizeof(acc_x) + sizeof(acc_y) + sizeof(acc_z), (char *)(&percent), sizeof(percent));

    size_t payload_length = sizeof(temperature) + sizeof(acc_x) + sizeof(acc_y) + sizeof(acc_z) + sizeof(percent);

    // for(int i = 0; i < payload_length; i++) {
    //     Serial.printf("%02x", payload[i]);
    // }
    // Serial.println();

    // std::cout << payload << std::endl;

    Serial.printf("  payload length: %i bytes\n", payload_length);
    // std::cout << "  central " << +central_node << std::endl;
    return Packet(char(int(random(10,50))), char(100), true, DATA, payload_length, payload);
}

void send_data_packet() {
    Packet p = create_data_packet();
    send_own_packet(&p);
    send_cnt++;

    double air_time = (12 + 4.25 + 8 + ceil( double(8*p.get_length() - 4*SF + 28)/(4*SF) )*CR )*symbol_duration;
    Serial.printf("  Should have taken %.2f ms \n",  air_time);
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

void update_display() {
    // display stuff
    display.clear();

    char buffer [50];
    sprintf(buffer, "lt: %lu", last_packet_duration);
    display.drawString(75, 0, buffer);
    // line 1
    sprintf(buffer, "sent: %i, rec: %i", send_cnt, rec_cnt);
    display.drawString(0, 10, buffer);

    // line 2
    sprintf(buffer, "TTS: %.1f s", (send_interval - (current_time - last_send_time))/1000.0 );
    display.drawString(0, 20, buffer);

    //line 5
    sprintf(buffer, "Battery:%i", percent);
    display.drawString(0, 50, buffer);

    display.display(); 
}

unsigned long get_time_since_start()
{
    return millis() + millisOffset;
}

void sleep_node(unsigned long sleepMillis)
{
    // sleep for specified time + offset to combat drift of inaccurate RTC clock
    esp_sleep_enable_timer_wakeup((sleepMillis + 1300) * 1000);
    // shift time by sleepMillis + offset to account for delay when shutting down 
    millisOffset = get_time_since_start() + sleepMillis + 98;
    esp_deep_sleep_start();
}