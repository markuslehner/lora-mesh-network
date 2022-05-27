#include <PacketHandler.h>
#include <Packet.h>
#include <Node.h>
#include <iostream>
#include <Arduino.h>
#include <LoRa.h>

// last sensor update
RTC_DATA_ATTR unsigned long last_send_time = 0; 
// update cycle time at beginning
RTC_DATA_ATTR unsigned long send_interval = 10000 - 1; // offset to account for internal delay

// statistics
RTC_DATA_ATTR unsigned long last_packet_duration = 0;

// packet handling
RTC_DATA_ATTR bool connected = false;
RTC_DATA_ATTR bool received_interval_data = false;
RTC_DATA_ATTR bool sending = false;
RTC_DATA_ATTR bool sleep_between_intervals = false;
RTC_DATA_ATTR char central_node = 0;
RTC_DATA_ATTR unsigned char packet_id = 0;
// between 0(=central) and 127
RTC_DATA_ATTR unsigned char distance = 127;

// packet handler params
const int relay_time = 2000;
const unsigned long relay_block_time = 60000;
const unsigned int relay_cnt = 2;
std::list<unsigned char> last_packet_origins;
std::list<unsigned long> last_packet_relay;
std::list<unsigned char> last_packet_pid;

//interval update
RTC_DATA_ATTR unsigned long last_interval = 0;
RTC_DATA_ATTR unsigned long next_sleep_interval = 0;
RTC_DATA_ATTR unsigned long interval_active_time = 0;
RTC_DATA_ATTR unsigned long interval_offset = 0;

// update block params
RTC_DATA_ATTR unsigned long last_interval_update = 0;
RTC_DATA_ATTR unsigned long interval_update_block = 15000;
const unsigned long request_block = 15000;
unsigned long last_requested_sent = 0;

std::list<QueuedPacket> packet_queue;


void queue_packet(Packet *p, int time_ms) {
    std::cout << "  queue packet for " << time_ms << std::endl;
    packet_queue.insert(packet_queue.end(), QueuedPacket(p, get_time_since_start() + time_ms));
}

void queue_own_packet(Packet *p, int time_ms) {
    //std::cout << "Queue.queue " << p << std::endl;
    (*p).packet_id = packet_id;
    packet_id++;
    queue_packet(p, time_ms);
}

void send_own_packet(Packet *p) {
    // std::cout << "  setting packet id " << +packet_id << std::endl;
    (*p).packet_id = packet_id;
    packet_id++;
    // std::cout << "  id " << +(*p).packet_id << std::endl;
    if((*p).max_hops == 0) {
        (*p).max_hops = (unsigned char) 7;
    }
    send_packet(p);
}

void send_packet(Packet *p) {
    (*p).sender = node_id;
    (*p).last_distance = distance;
    (*p).num_hops++;

    #ifdef TESTING
        world->send_packet(p);
    #else
        if((*p).origin == node_id) {
            if((*p).type == COMMAND || (*p).type == COMMAND_ACK) {
                Serial.printf("Sending own COMMAND (%i) packet: PID: %i, type %i \n", (*p).payload[0] ,(*p).packet_id, (*p).type);
            } else {
                Serial.printf("Sending own packet: PID: %i, type %i \n",  (*p).packet_id, (*p).type);
            }
        } else {
            if((*p).type == COMMAND || (*p).type == COMMAND_ACK) {
                Serial.printf("Sending COMMAND (%i) packet: PID: %i, type %i \n", (*p).payload[1], (*p).packet_id, (*p).type);
            } else {
                Serial.printf("Sending packet: PID: %i, type %i \n",  (*p).packet_id, (*p).type);
            } 
        }

        char data_buffer[100];
        (*p).to_bytes(app_id, data_buffer);
        LoRa.beginPacket();
        size_t byte_cnt = 0;
        for (int i = 0; i < (*p).get_length(); i++) {
            // Serial.printf("%02x", data_buffer[i]);
            byte_cnt += LoRa.print(data_buffer[i]);
        }
        // Serial.println();
        unsigned long tx_start = get_time_since_start();
        LoRa.endPacket();
        last_packet_duration = get_time_since_start()- tx_start;
        Serial.printf("  Sending took: %lu ms \n",  last_packet_duration);
        Serial.printf("  Sent %i bytes \n",  byte_cnt);
    #endif
}

int length() {
    return packet_queue.size();
}

unsigned char get_node_id() {
    return node_id;
}

void handle_packet(Packet *p) {
    std::cout << "  handle packet" << std::endl;
    unsigned int num_blocks = get_num_received(p);
    if(num_blocks < 1) {
        if( (*p).target == node_id) {
            handle_own_packet(p);
        } else {
            handle_foreign_packet(p);
            if(num_blocks < relay_cnt) {
                relay_packet(p);
            } else {
                Serial.printf("  Not relaying bc: relay block (%u >= %u)\n", num_blocks, relay_cnt);
            }
        }
    }
    add_packet_to_storage(p);
}

void handle_own_packet(Packet *p) {
    std::cout << "  Received packet for node: ";
    if(connected) {
        // ACK
        if( (*p).type == ACK){
            std::cout << "ACK";
            std::cout << " from " << +(*p).origin << std::endl;
        
        } else if( (*p).type == JOIN_ACK ) {
            std::cout << "JOIN_ACK";
            std::cout << " from " << +(*p).origin << " , but already connected" << std::endl;

        // COMMAND
        } else if( (*p).type == COMMAND or (*p).type == COMMAND_ACK) {
            std::cout << "  COMMAND-->";

            // if sending of an ACK is required
            bool send_ack = (*p).type == COMMAND_ACK;
            // flag to signal success and trigger sending of ACK if send_ack = true
            bool success = false;

            // SET_INTERVAL
            if( (*p).payload[0] == SET_INTERVAL ) {
                std::cout << "SET_INTERVAL" << std::endl;

                if(get_time_since_start() - last_interval_update > interval_update_block) {
                    last_interval_update = get_time_since_start();
                    
                    // SF 10 
                    // unsigned int est_time_delay = 403 + ((*p).num_hops-1)*(403 + relay_time/2);
                    // SF 7
                    unsigned int est_time_delay = 46 + ((*p).num_hops-1)*(46 + relay_time/2);

                    std::cout << "  est delay time "<< +est_time_delay << std::endl;

                    unsigned int interval;
                    unsigned int interval_active_t;
                    unsigned int interval_off;
                    unsigned int next_interval_start;
                    bool start_sending;

                    memcpy(&interval, (*p).payload+1, 4);
                    memcpy(&interval_active_t, (*p).payload+5, 4);
                    memcpy(&interval_off, (*p).payload+9, 4);
                    memcpy(&next_interval_start, (*p).payload+13, 4);
                    start_sending = ((unsigned char)(*p).payload[17] ) > 0;

                    std::cout << "  interval "<< +interval << std::endl;
                    std::cout << "  interval_active_time "<< +interval_active_t << std::endl;
                    std::cout << "  interval_offset "<< +interval_off << std::endl;
                    std::cout << "  next_interval_start "<< +next_interval_start << std::endl;
                    std::cout << "  start sending "<< +start_sending << std::endl;

                    // update own sending params
                    // central sent time until next interval start = payload[4]
                    // calculate the local time at which this happens
                    send_interval = interval;
                    interval_active_time = interval_active_t;
                    next_interval_start = get_time_since_start() + next_interval_start - est_time_delay;
                    // set next sleeping interval
                    next_sleep_interval = next_interval_start + interval_active_time;
                    last_send_time = next_interval_start + interval_off - interval;
                    interval_offset = interval_off;
                    last_interval = next_interval_start - interval;
                    sending = start_sending;

                    received_interval_data = true;

                    // ACK packet
                    send_ack = true;
                    success = true;
                } else {
                    std::cout << "  BLOCKED" << std::endl;
                }  
            // RESYNC_INTERRVAL
            } else if( (*p).payload[0] == RESYNC_INTERVAL ) {
                std::cout << "RESYNC_INTERVAL" << std::endl;
                if(received_interval_data && get_time_since_start() - last_interval_update > interval_update_block) {
                    last_interval_update = get_time_since_start();

                    unsigned int est_time_delay = 403 + ((*p).num_hops-1)*(403 + relay_time/2);
                    std::cout << "  est delay time "<< +est_time_delay << std::endl;

                    unsigned int next_interval_start;
                    memcpy(&next_interval_start, (*p).payload+1, 4);

                    std::cout << "  next_interval_start "<< +next_interval_start << std::endl;

                    // update own sending params
                    // central sent time until next interval start = payload[4]
                    // calculate the local time at which this happens
                    next_interval_start = get_time_since_start() + next_interval_start - est_time_delay;
                    // set next sleeping interval
                    next_sleep_interval = next_interval_start - send_interval + interval_active_time;
                    last_send_time = next_interval_start + interval_offset - send_interval;
                    last_interval = next_interval_start - send_interval;
                }
            // REQUEST
            } else if ( (*p).payload[0] == REQUEST ) {
                std::cout << "REQUEST" << std::endl;

                if(get_time_since_start() - last_requested_sent > request_block) {
                    last_requested_sent = get_time_since_start();
                    std::cout << "  RESENDING DATA PACKET..." << std::endl;

                    Packet p = create_data_packet();
                    queue_own_packet(&p, get_random_number(300, 700));
                }
            // RESET
            } else if ( (*p).payload[0] == RESET ) {
                std::cout << "RESET" << std::endl;
                std::cout << "RESETING..." << std::endl;
                ESP.restart();
            //START_SENDING
            } else  if ( (*p).payload[0] == START_SENDING ) {
                std::cout << "START_SENDING" << std::endl;
                if(received_interval_data) {
                    sending = true;
                }
            //STOP_SENDING
            } else if ( (*p).payload[0] == STOP_SENDING ) {
                std::cout << "STOP_SENDING" << std::endl;
                sending = false;
                success = true;
            //ENABLE_SLEEP
            } else if ( (*p).payload[0] == ENABLE_SLEEP ) {
                std::cout << "ENABLE_SLEEP" << std::endl;
                sleep_between_intervals = true;
                success = true;
            //DISABLE_SLEEP
            } else if ( (*p).payload[0] == DISABLE_SLEEP ) {
                std::cout << "DISABLE_SLEEP" << std::endl;
                sleep_between_intervals = false;
                success = true;
            //ENABLE_DEBUG
            } else if ( (*p).payload[0] == ENABLE_DEBUG ) {
                std::cout << "ENABLE_DEBUG" << std::endl;
                set_debug(true);
                success = true;
            //DISABLE_DEBUG
            } else if ( (*p).payload[0] == DISABLE_DEBUG ) {
                std::cout << "DISABLE_DEBUG" << std::endl;
                set_debug(false);
                success = true;
            //SET_BLOCK
            } else if ( (*p).payload[0] == SET_BLOCK ) {
                std::cout << "SET_BLOCK" << std::endl;
                add_artificial_block((*p).payload[1]);
                success = true;                    
            //REMOVE_BLOCK
            } else if ( (*p).payload[0] == REMOVE_BLOCK ) {
                std::cout << "REMOVE_BLOCK" << std::endl;
                remove_artificial_block((*p).payload[1]);
                success = true;
            //SET_DISTANCE
            } else if ( (*p).payload[0] == SET_DISTANCE ) {
                std::cout << "SET_DISTANCE" << std::endl;
                std::cout << "  SETTING DISTANCE TO: " << +(*p).payload[1] << std::endl;
                distance = (*p).payload[1];
                success = true;
            } else if ( (*p).payload[0] == REQUEST_ROUTE ) {
                std::cout << "REQUEST_ROUTE" << std::endl;
                unsigned char payload[7];

                // Packet p(node_id, node_id, (unsigned char) central_node, packet_id, (unsigned char) 7, 10, true, ROUTE, 10, payload);
                Packet p(node_id, central_node, true, ROUTE, 7, payload);
                p.max_hops = 8;
                std::cout << "  SENDING ROUTE" << std::endl;
                queue_own_packet(&p, 1000);
            } else {
                std::cout << "  UNKNOWN COMMAND FOR NODE" << +(*p).payload[0] << std::endl;
            }

            if(send_ack && success) {

                unsigned char payload[1];
                payload[0] = (*p).packet_id;

                // Packet p(node_id, node_id, (unsigned char) central_node, packet_id, (unsigned char) 7, 10, true, ACK, 1, payload);
                Packet p(node_id, central_node, true, ACK, 1, payload);
                std::cout << "  SENDING ACK" << std::endl;
                queue_own_packet(&p, 1000);
            }

        }
    } else {
        // ACK
        if( (*p).type == JOIN_ACK) {
            std::cout << "ACK" << std::endl;
            central_node = (*p).payload[0];
            distance = (*p).payload[1];
            connected = true;

            // reset interval data to avoid updating multiple times
            last_interval = get_time_since_start();
            last_send_time = get_time_since_start();
            next_sleep_interval = get_time_since_start() + send_interval;

            std::cout << "  Sucessfully registered with central " << +central_node << " dist " << +distance << std::endl;
        }
    }
}

void handle_foreign_packet(Packet *p) {
    std::cout << "  other packet: ";
    if(connected) {
        // JOIN
        if( (*p).type == JOIN and (*p).last_distance == 127) {
            std::cout << "  RECEIVED JOIN FROM NEW NODE" << std::endl;
            (*p).payload[0] = LoRa.packetRssi();
            (*p).payload[1] = node_id;

        } else if( (*p).type == ROUTE) {
            std::cout << "  ADDING ROUTE INFO" << std::endl;
            (*p).payload[int( (*p).num_hops - 1)] = node_id;

        } else if( (*p).type == COMMAND) {

            std::cout << "  COMMAND -->";
            // check if it is a broadcast message, as to not execute command for other node
            if( (*p).target == 0) {
                if ( (*p).payload[0] == 243 ) {
                    std::cout << "START_SENDING" << std::endl;
                    if(received_interval_data) {
                        sending = true;
                    }
                } else if ( (*p).payload[0] == 252 ) {
                    std::cout << "STOP_SENDING" << std::endl;
                    sending = false;

                } else if ( (*p).payload[0] == 15 ) {
                    std::cout << "ENABLE_SLEEP" << std::endl;
                    sleep_between_intervals = true;

                } else if ( (*p).payload[0] == 3 ) {
                    std::cout << "DISABLE_SLEEP" << std::endl;
                    sleep_between_intervals = false;

                } else if( (*p).payload[0] == RESYNC_INTERVAL ) {
                    std::cout << "RESYNC_INTERVAL" << std::endl;
                    if(received_interval_data && get_time_since_start() - last_interval_update > interval_update_block) {
                        last_interval_update = get_time_since_start();

                        unsigned int est_time_delay = 403 + ((*p).num_hops-1)*(403 + relay_time/2);
                        std::cout << "  est delay time "<< +est_time_delay << std::endl;

                        unsigned int next_interval_start;
                        memcpy(&next_interval_start, (*p).payload+1, 4);

                        std::cout << "  next_interval_start "<< +next_interval_start << std::endl;

                        // update own sending params
                        // central sent time until next interval start = payload[4]
                        // calculate the local time at which this happens
                        next_interval_start = get_time_since_start() + next_interval_start - est_time_delay;
                        // set next sleeping interval
                        next_sleep_interval = next_interval_start - send_interval + interval_active_time;
                        last_send_time = next_interval_start + interval_offset - send_interval;
                        last_interval = next_interval_start - send_interval;
                    }
                } else {
                    std::cout << "OTHER/UNKNOWN BROADCAST PACKET: " << +(*p).payload[0] << std::endl;
                }

            } else {
                if ( (*p).payload[0] == SET_INTERVAL ) {

                    std::cout << "SET_INTERVAL FROM OTHER" << std::endl;
                    unsigned int interval_active_t;
                    memcpy(&interval_active_t, (*p).payload+5, 4);

                    if(interval_active_time > 0 && interval_active_time != interval_active_t) {
                        std::cout << "  UPDATE ACTIVE TIME" << std::endl;
                        next_sleep_interval += ( interval_active_t - interval_active_time );
                        interval_active_time = interval_active_t;
                    } else {
                        std::cout << "  ALREADY UP TO DATE" << std::endl;
                    }
                } else {
                    std::cout << "  Not applicable for node. Command-type: " << +(*p).payload[0] << std::endl;
                }
            }
        } else {
            std::cout << "  Not applicable for node." << std::endl;
        }
    } else {
            std::cout << "Not connected, no forwarding!" << std::endl;
    }
}

void relay_packet(Packet *p) {

    if( (*p).target == node_id ) {
        std::cout << "  Not relaying bc: REACHED DESTINATION" << std::endl;
    } else if( (*p).origin == node_id ) {
        std::cout << "  Not relaying bc: return to origin" << std::endl;
    } else if( (*p).sender == node_id) {
        std::cout << "  Not relaying bc: return to sender" << std::endl;
    } else if( (*p).direction && (*p).last_distance <= distance ) {
        std::cout << "  Not relaying bc: distance --> up" << std::endl;
    } else if( !(*p).direction && (*p).last_distance >= distance ) {
        std::cout << "  Not relaying bc: distance <-- down" << std::endl;
    }else {
        queue_packet(p, get_random_number(0, relay_time));
    }
}

void add_packet_to_storage(Packet *p) {
    last_packet_origins.insert(last_packet_origins.end(), (*p).origin);
    last_packet_relay.insert(last_packet_relay.end(), get_time_since_start());
    last_packet_pid.insert(last_packet_pid.end(), (*p).packet_id);
}

// return number of times this packet was already forwarded within the timespan specified by relay_block_time
// @param packet The received packet
unsigned int get_num_received(Packet *p) {

    // check if packet is a join packet
    if((*p).type == JOIN) {
        return 0;
    }

    // check if forwarded packet from this origin in the last time
    unsigned int num_blocks = 0;
    unsigned long largest_blocking_time = 0;

    std::list<unsigned char>::iterator it_nid = last_packet_origins.begin();
    std::list<unsigned long>::iterator it_time = last_packet_relay.begin();
    std::list<unsigned char>::iterator it_pid = last_packet_pid.begin();

    while (it_nid != last_packet_origins.end()) {
        // Serial.printf("  checking packet entrys (ID: %u/%u, PID: %u/%u)\n", *it_nid, (*p).origin, *it_pid, (*p).packet_id);
        if((*p).type != (unsigned char) ROUTE && *it_nid == (*p).origin && *it_pid == (*p).packet_id) {

            // get the time since entry in relay block list
            unsigned long blocking_time = get_time_since_start() - *it_time;
            // check if time is smaller than relay block --> is blocking
            // Serial.printf("  time: %lu, p_time: %lu, diff: %lu\n", get_time_since_start(), *it_time, get_time_since_start() - *it_time);
            if(blocking_time < relay_block_time) {
                //Serial.printf("    adding block\n");
                num_blocks++;
                // keep track of oldest entry in relay_block_list for debugging
                if(largest_blocking_time < blocking_time) {
                    largest_blocking_time = blocking_time;
                }
            } else {
                //Serial.printf("  removing index from block list\n");
                last_packet_origins.erase(it_nid);
                last_packet_relay.erase(it_time);
                last_packet_pid.erase(it_pid);
            }
        } else {
            if(get_time_since_start() - *it_time > relay_block_time) {
                //Serial.printf("  removing index from block list\n");
                last_packet_origins.erase(it_nid);
                last_packet_relay.erase(it_time);
                last_packet_pid.erase(it_pid);
            }
        }
        
        // advance iterators
        if(it_nid != last_packet_origins.end()) {
            //Serial.printf("  advancing iterators\n");
            it_nid++;
            it_time++;
            it_pid++;
        }
    }
    
    // for (int i = 0; i < last_packet_origins.size(); i++) {
    //     last_packet_relay.erase(remove[i]-i)
    //     last_packet_origins.pop(remove[i]-i)
    //     node.debugger.log("Node %s: removed entry from block list, %i remaining" % (self.node.name, len(self.last_packet_relay)), 4)
    // }
        
    
    return num_blocks;
}

unsigned int get_random_number(unsigned int start, unsigned int stop) {

    return random(start, stop);
}

void update() {

    if( length() > 0 ) {

        bool remove = false;
        std::list<QueuedPacket>::iterator it;

        for (it = packet_queue.begin(); it != packet_queue.end(); ++it){
            if( get_time_since_start() > it->send_time ) {
                remove = true;
                break;
            }
        }

        if(remove) {
            // send packet
            send_packet(&it->packet);
            // remove packet from list
            packet_queue.erase(it);
        }
    }
}
