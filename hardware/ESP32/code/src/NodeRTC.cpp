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

// sensor
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

#include <Node.h>

// I2C pins for sensor
#define MPU_SDA 33
#define MPU_SCL 32

// if RTC DS3231 has same addr 0x68 as MPU6050, so pull AD0 a MPU high to change address to 0x69
#ifdef RTC_PRESENT
    #define MPU_ADDR 0x69
    #include "RTClib.h"
    RTC_DS3231 rtc;
#else
    #define MPU_ADDR MPU6050_I2CADDR_DEFAULT
#endif

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

// sensor
Adafruit_MPU6050 mpu;
float acc_x, acc_y, acc_z, temperature;

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

// artificial blocks
// and node switching with environments
#ifdef NODE_199
    RTC_DATA_ATTR unsigned char art_blocks[10] {155, 133};
    RTC_DATA_ATTR unsigned char num_blocks = 2;
    const char node_id = 10;
    const int skip_every = 0;
    #define SLEEP_OFFSET 1300
#endif
#ifdef NODE_177
    RTC_DATA_ATTR unsigned char art_blocks[10] {100};
    RTC_DATA_ATTR unsigned char num_blocks = 1;
    const char node_id = 177;
    const int skip_every = 0;
    #define SLEEP_OFFSET 1300
#endif
#ifdef NODE_155
    RTC_DATA_ATTR unsigned char art_blocks[10] {100, 199};
    RTC_DATA_ATTR unsigned char num_blocks = 2;
    const char node_id = 155;
    const int skip_every = 0;
    #define SLEEP_OFFSET 1300
#endif
#ifdef NODE_133
    RTC_DATA_ATTR unsigned char art_blocks[10] {100, 199};
    RTC_DATA_ATTR unsigned char num_blocks = 2;
    const char node_id = 133;
    const int skip_every = 0;
    #define SLEEP_OFFSET 1300
#endif

//node logic
#ifndef NO_LORA
    const int SF = 7;
    const int CR = 5;
    const unsigned long BW = 125000;
    const int tx_power = 14;
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
unsigned long join_retry_interval = 15000 - 2; // offset to account for internal delay

// if node is sleeping
bool sleeping = false;
unsigned long next_wakeup;
unsigned long sleep_time;

// debug toggle
// if true, console output and display are enabled
RTC_DATA_ATTR bool debug = true;

// statistics
RTC_DATA_ATTR int send_cnt = 0;
RTC_DATA_ATTR int rec_cnt = 0;

// sleep
RTC_DATA_ATTR unsigned long millisOffset = START_TIME;


// forward declaration of methods
size_t append_data(char * data_ptr, size_t length, bool up);
Packet create_data_packet();
Packet create_empty_packet();
void receive_packet();

void setup() {
    Serial.begin(9600);
    while (!Serial);

    Serial.println("LoRa Node:");
    Serial.printf("  ID: %i\n", (unsigned int) node_id);
    Serial.printf("  APP_ID: %i\n", app_id[0]*256 + app_id[1]);
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

    #ifdef RTC_PRESENT
        // init clock
        if (! rtc.begin(&Wire)) {
            Serial.println("Couldn't find RTC");
            Serial.flush();
            while (1) delay(10);
        } 
    #endif

    get_battery_voltage();

    if(!debug) {
        display.displayOff();
    }
}

void loop() {

    update();

    int packetSize = LoRa.parsePacket();
    if (packetSize) {
        receive_packet();
    }

    current_time = get_time_since_start();
    if ( connected) {

        // check for corupted cycle
        if(last_interval > current_time) {
            std::cout << "RESTARTING DUE TO INTERVAL CORRUPTION" << std::endl;
            ESP.restart();
        } else if (last_send_time > current_time) {
            std::cout << "RESTARTING DUE TO SEND-INTERVAL CORRUPTION" << std::endl;
            ESP.restart();
        }

        // start interval
        if (current_time - last_interval > send_interval) {
            last_interval += send_interval;

            std::cout << "INTERVAL START" << std::endl;
        }

        // sending
        if (current_time - last_send_time > send_interval) {

            last_send_time += send_interval;

            get_battery_voltage();

            if(sending) {
                // skip every # packet, to test REQUEST functionality
                // or send always if skip_every = 0
                if(skip_every == 0 || send_cnt % skip_every != 0) {
                    Serial.print("Sending DATA packet: ");
                    Serial.println(send_cnt);

                    #ifdef NO_LORA
                        Serial.println("LoRa disabled");
                        send_cnt++;
                    #else
                        send_data_packet();
                    #endif
                } else {
                    send_cnt++;
                }
            }

            #ifdef RTC_PRESENT
                DateTime now = rtc.now();
                Serial.println("RTC Time:");
                Serial.println(now.second());
            #endif
        }

        if ( next_sleep_interval < current_time) {
            std::cout << "INTERVAL ACTIVE END" << std::endl;

            next_sleep_interval += send_interval;
            sleep_time = next_sleep_interval - get_time_since_start() - interval_active_time - 3000;
            next_wakeup = sleep_time + get_time_since_start();
            sleeping=true;

            if(sleep_between_intervals) {
                // set sleep state
                #ifndef NO_LORA
                    LoRa.sleep();
                #endif
                display.displayOff();
                mpu.enableSleep(true);

                std::cout << "STARTED SLEEPING" << std::endl;
                // recalculate to get combat drift
                sleep_time = next_sleep_interval - get_time_since_start() - interval_active_time - 3000;
                sleep_node(sleep_time);
            }
        }

        if ( sleeping && next_wakeup < current_time) {
            sleeping=false;
            std::cout << "WAKING UP" << std::endl;
        }

    } else {
        current_time = get_time_since_start();
        if( current_time - last_join_time > join_retry_interval) {
            // set next join time, add jitter of +4 seconds
            last_join_time = current_time - random(1, 4000);

            get_battery_voltage();

            // create packet, packet type JOIN == 240
            unsigned char payload[2];
            payload[0] = 0;
            payload[1] = node_id;
            Packet p(node_id, central_node, true, 240, 2, payload);
            Serial.println("Sending JOIN packet: ");
            send_own_packet(&p);
        }
    }

    // update display
    current_time = get_time_since_start();
    if (current_time - last_display_update_time > display_update_interval) {

        last_display_update_time = current_time;
        update_display();
    }
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

    if(debug) {

        // display stuff
        display.clear();

        char buffer [50];
        // line 0
        sprintf(buffer, "con: %i, ID:%i", connected, node_id);
        display.drawString(0, 0, buffer);
        sprintf(buffer, "lt: %lu", last_packet_duration);
        display.drawString(75, 0, buffer);
        // line 1
        sprintf(buffer, "sent: %i, rec: %i", send_cnt, rec_cnt);
        display.drawString(0, 10, buffer);

        // line 2 + 3
        if(connected) {
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
        }

        // line 4
        sprintf(buffer, "Send: %i, sleep: %i", sending, sleep_between_intervals);
        display.drawString(0, 40, buffer);
        if(sleeping) {
            sprintf(buffer, "OFF");
        } else {
            sprintf(buffer, "ON");
        }
        display.drawString(90, 40, buffer);

        //line 5
        sprintf(buffer, "Battery:%i", percent);
        display.drawString(0, 50, buffer);
        sprintf(buffer, "Dist:%i->%i", distance, central_node);
        display.drawString(55, 50, buffer);

        display.display(); 
    }
}

void receive_packet() {
    // received a packet
    Serial.print("Received packet with RSSI: ");
    Serial.println(LoRa.packetRssi());

    // read packet
    unsigned char rec_buffer[50];
    int byte_cnt = 0;
    while (LoRa.available()) {
        rec_buffer[byte_cnt] = (unsigned char)LoRa.read();
        //Serial.print(rec_buffer[byte_cnt]);
        byte_cnt++;
    }  

    if(app_id[0] == rec_buffer[0] && app_id[1] == rec_buffer[1]) {
        // Serial.println("->Packet was from same network!");
        // for(int i = 0; i < byte_cnt; i++) {
        //     Serial.printf("%02x", rec_buffer[i]);
        // }
        // Serial.println();

        // decoding
        // Serial.printf("  Sender: %i\n", rec_buffer[2]);
        // Serial.printf("  Origin: %i\n", rec_buffer[3]);
        // Serial.printf("  Target: %i\n", rec_buffer[4]);
        // Serial.printf("  Hops: %u / %u\n", rec_buffer[5]&15, rec_buffer[5]>>4);
        // Serial.printf("  Packet-ID: %i\n", rec_buffer[6]);
        // Serial.printf("  Dir: %i, last_dist: %i\n", rec_buffer[7]>>7, rec_buffer[7]&127);
        // Serial.printf("  PL-Type: %i\n", rec_buffer[8]);

        Packet p(rec_buffer[2], rec_buffer[3], rec_buffer[4], rec_buffer[6], rec_buffer[5]>>4, rec_buffer[7]&127, rec_buffer[3]>>7, rec_buffer[8], byte_cnt-9, rec_buffer+9);
        p.num_hops = rec_buffer[5]&15;

        // check for artifical block      
        bool blocked = false;
        for(int i = 0; i < num_blocks; i++) {
            if(art_blocks[i] == p.sender) {
                blocked = true;
                break;
            }
        }

        // check if packet is REMOVE_BLOCK
        if(blocked && p.target == node_id && ( p.type == COMMAND || p.type == COMMAND_ACK) && p.payload[0] == REMOVE_BLOCK) {
            blocked = false;
            Serial.printf("  Overriding artificial block because of REMOVE_BLOCK packet\n");
        }

        if(blocked) {
            Serial.printf("  not handling packet from %i, because of artificial block\n", p.sender);
        } else {
            handle_packet(&p);
        }

        rec_cnt++;
    }     
}

Packet create_data_packet() {

    #ifdef NO_SENSOR
        temperature = 0;
        acc_x = 0;
        acc_y = 0;
        acc_z = 0;
    #else
        mpu.enableSleep(false);

        sensors_event_t a, g, temp;
        mpu.getEvent(&a, &g, &temp);

        Serial.print("\t\tTemperature ");
        Serial.print(temp.temperature);
        Serial.println(" deg C");

        Serial.print("Accelerometer ");
        Serial.print("X: ");
        Serial.print(a.acceleration.x, 1);
        Serial.print(" m/s^2, ");
        Serial.print("Y: ");
        Serial.print(a.acceleration.y, 1);
        Serial.print(" m/s^2, ");
        Serial.print("Z: ");
        Serial.print(a.acceleration.z, 1);
        Serial.println(" m/s^2");

        temperature = temp.temperature;
        acc_x = a.acceleration.x;
        acc_y = a.acceleration.y;
        acc_z = a.acceleration.z;

        mpu.enableSleep(true);
    #endif

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
    return Packet(node_id, central_node, true, DATA, payload_length, payload);
}

void send_data_packet() {
    Packet p = create_data_packet();
    send_own_packet(&p);
    send_cnt++;

    double air_time = (12 + 4.25 + 8 + ceil( double(8*p.get_length() - 4*SF + 28)/(4*SF) )*CR )*symbol_duration;
    Serial.printf("  Should have taken %.2f ms \n",  air_time);
}

void set_debug(bool d) {
    debug = d;

    if(debug) {
        display.displayOn();
    } else {
        display.displayOff();
    }
}

void add_artificial_block(unsigned char block) {
    bool blocked = false;
    for(int i = 0; i < num_blocks; i++) {
        if(art_blocks[i] == block) {
            blocked = true;
            break;
        }
    }
    if(blocked) {
        Serial.printf("  Node %i already on block list\n",  block);
    } else {
        if(num_blocks < 9) {
            art_blocks[int(num_blocks)] = block;
            num_blocks++;
            Serial.printf("  Node %i added to block list\n",  block);
        } else {
            Serial.printf("  Block-list full, not adding node %i\n",  block);
        }
    }
}

void remove_artificial_block(unsigned char block) {
    bool blocked = false;
    int i;
    for(i = 0; i < num_blocks; i++) {
        if(art_blocks[i] == block) {
            blocked = true;
            break;
        }
    }
    if(blocked) {
        Serial.printf("  Node %i is pos %i on block list\n",  block, i);
        for(int k = i+1; k < num_blocks; k++) {
            
        }
        art_blocks[int(num_blocks)-1] = 0;
        num_blocks--;
    } else {
        Serial.printf("  Node %i not on block list\n",  block);
    }
}

unsigned long get_time_since_start()
{
    return millis() + millisOffset;
}

void sleep_node(unsigned long sleepMillis)
{
    // sleep for specified time + offset to combat drift of inaccurate RTC clock
    esp_sleep_enable_timer_wakeup((sleepMillis + SLEEP_OFFSET) * 1000);
    // shift time by sleepMillis + offset to account for delay when shutting down 
    millisOffset = get_time_since_start() + sleepMillis + 98;
    esp_deep_sleep_start();
}