#ifndef PACKET_H
#define PACKET_H

#include <cstddef>


class Packet {

    public:
        unsigned char type;
        unsigned char sender;
        unsigned char origin;
        unsigned char target;
        unsigned char packet_id;
        unsigned char num_hops;
        unsigned char max_hops;
        unsigned char last_distance;
        bool direction;

        unsigned char payload_length;
        char payload[32];

        void change_payload(size_t pay_l, unsigned char* pay);
        void append_payload(char * data_ptr, size_t length, bool up);
        void to_bytes(const unsigned char* app_id, char* buffer);
        size_t get_length();
        Packet* clone();

        // constructors
        Packet(unsigned char s, unsigned char o, unsigned char ta, unsigned char pid, unsigned char max_h, unsigned char last_d, bool dir, unsigned char t, size_t pay_l, unsigned char pay[]);
        Packet(unsigned char o, unsigned char ta, bool dir, unsigned char t, size_t pay_l, unsigned char pay[]);
        Packet() = default;
        Packet( const Packet &obs);
};

#endif