#ifndef PACKET_QUEUE_H
#define PACKET_QUEUE_H

#include <Packet.h>
#include <list>
#include <iostream>

class QueuedPacket {
    public:
        Packet packet;   // the packet
        unsigned long send_time;    // time when the packet is supposed to be sent in ms

        QueuedPacket(Packet *p, unsigned long t) {
            // std::cout << "QueuedPacket " << p << std::endl;
            packet = *p;
            send_time = t;
        }
};

// update parameters
extern bool connected;
extern bool received_interval_data;
extern bool sending;
extern bool sleep_between_intervals;

extern unsigned long last_send_time;
extern unsigned long interval_active_time;
extern unsigned long send_interval;
extern unsigned long last_interval;
extern unsigned long next_sleep_interval;
extern unsigned long interval_offset;
extern unsigned char distance;

// application parameters
extern char central_node;
extern unsigned char packet_id;
//update block parameters
extern unsigned long last_interval_update;
extern unsigned long interval_update_block;
extern unsigned long last_requested_sent;

// relay parameters
extern const int relay_time;
extern const unsigned long relay_block_time;
extern const unsigned int relay_cnt;
extern std::list<unsigned char> last_packet_origins;
extern std::list<unsigned long> last_packet_relay;
extern std::list<unsigned char> last_packet_pid;

// statistics
extern unsigned long last_packet_duration;

// queue
extern std::list<QueuedPacket> packet_queue;

void update();
void queue_packet(Packet *p, int time_ms);
void queue_own_packet(Packet *p, int time_ms);
void send_packet(Packet *p);
void send_own_packet(Packet *p);
void handle_packet(Packet *p);
void handle_own_packet(Packet *p);
void handle_foreign_packet(Packet *p);
void add_packet_to_storage(Packet *p);
void relay_packet(Packet *p);
unsigned int get_random_number(unsigned int start, unsigned int stop); 
unsigned int get_num_received(Packet *p);
int length();
unsigned char get_node_id();

#endif