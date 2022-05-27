#ifndef NODE_H
#define NODE_H

#include <Packet.h>

enum packet_type {
    ACK = 255,
    JOIN_ACK = 15,
    COMMAND = 189,
    COMMAND_ACK = 66,
    JOIN = 240,
    ROUTE = 77,
    DATA = 0
};

enum command_type {
    ENABLE_DEBUG = 192,
    DISABLE_DEBUG = 195,
    REQUEST = 207, 
    RESET = 0,
    START_SENDING = 243,
    STOP_SENDING = 252,
    ENABLE_SLEEP = 15,
    DISABLE_SLEEP = 3,
    SET_INTERVAL = 213,
    SET_BLOCK = 60,
    REMOVE_BLOCK = 51,
    SET_DISTANCE = 174,
    REQUEST_ROUTE = 77,
    RESYNC_INTERVAL = 108
};

extern const char node_id;
extern const unsigned char app_id[2];
// artificial blocks
extern unsigned char art_blocks[10];
extern unsigned char num_blocks;

void send_data_packet();
Packet create_data_packet();
void set_debug(bool d);
void update_display();
void get_battery_voltage();
unsigned long get_time_since_start();
void sleep_node(unsigned long time);
void add_artificial_block(unsigned char block);
void remove_artificial_block(unsigned char block);

#endif