#include <Packet.h>
#include <string.h>
#include <iostream>
#include <stdio.h>

#include <cstddef>

Packet::Packet(unsigned char s, unsigned char o, unsigned char ta, unsigned char pid, unsigned char max_h, unsigned char last_d, bool dir, unsigned char t, size_t pay_l, unsigned char* pay) {
    sender = s;
    origin = o;
    target = ta;
    packet_id = pid;
    max_hops = max_h;
    num_hops = 0;
    last_distance = last_d;
    direction = dir;
    type = t;
    payload_length = pay_l;
    if(payload_length > 0) {
        memcpy(payload, pay, pay_l);
    }

    // std::cout << "Packet" << std::endl;
    // std::cout << pay << std::endl;

    // char buffer[20];
    // for(int i = 0; i < payload_length; i++) {
    //     sprintf(buffer, "%02x", pay[i]);
    //     std::cout << buffer;
    // }
    // std::cout << std::endl;
}

Packet::Packet(unsigned char o, unsigned char ta, bool dir, unsigned char t, size_t pay_l, unsigned char* pay) {
    origin = o;
    target = ta;
    num_hops = 0;
    max_hops = (unsigned char) 7;
    type = t;
    direction = dir;
    payload_length = pay_l;
    if(payload_length > 0) {
        memcpy(payload, pay, pay_l);
    }
}

Packet::Packet( const Packet &obs) {

    // std::cout << "copying packet" << std::endl;

    type = obs.type;
    sender = obs.sender;
    origin = obs.origin;
    target = obs.target;
    packet_id = obs.packet_id;
    num_hops = obs.num_hops;
    max_hops = obs.max_hops;
    last_distance = obs.last_distance;
    direction = obs.direction;
    payload_length = obs.payload_length;
    if(obs.payload_length > 0) {
        memcpy(payload, obs.payload, payload_length);
    }
}

Packet* Packet::clone() {
    return new Packet(*this);
}

void Packet::change_payload(size_t pay_l, unsigned char pay[]) {
    payload_length = pay_l;
    memcpy(payload, pay, pay_l);
}

void append_payload(char * data_ptr, size_t length, bool up) {
    // if (!up) { data_ptr += length-1; }
    // size_t bytes = 0;
    // for (int i = 0; i < length; ++i)
    // {
    //     bytes += LoRa.print(*data_ptr);
    //     Serial.printf("%02x", *data_ptr);
    //     // Serial.printf("%p \n", p);
    //     if(up) {
    //         data_ptr++;
    //     } else {
    //         data_ptr--;
    //     }
        
    // }
}

void Packet::to_bytes(const unsigned char* app_id, char* buffer) {

    //app id
    buffer[0] = app_id[0];
    buffer[1] = app_id[1];

    buffer[2] = sender;
    buffer[3] = origin;
    buffer[4] = target;
    buffer[5] = max_hops*16 + num_hops;
    buffer[6] = packet_id;
    buffer[7] = direction*128 + last_distance;
    buffer[8] = type;

    if(payload_length > 0) {
        memcpy(buffer+9, payload, payload_length);
    }
}

size_t Packet::get_length() {
    return 9 + payload_length;
}