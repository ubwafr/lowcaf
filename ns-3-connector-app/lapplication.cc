/**
 * @file lapplication.h
 * @author ubwmst
 * @brief NS-3 connector application for the Lowcaf framework
 * @version 0.1
 * @date 2024-02
 *
 * @copyright Copyright (c) 2024
 *
 */
#include "lapplication.h"

#include "ns3/application.h"
#include "ns3/core-module.h"
#include "ns3/network-module.h"

#include <arpa/inet.h>
#include <endian.h>
#include <iostream>
#include <malloc.h>
#include <math.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <thread>
#include <unistd.h>

using namespace ns3;

namespace ns3
{

    NS_LOG_COMPONENT_DEFINE("LApplication");

    /**
     * @brief Helper to convert MAC48 byte representation into string representation
     *
     * @param mac
     * @return char*
     */
    char *
    mac48tostr(u_int8_t *mac)
    {
        char *res = (char *)malloc(18);
        for (int i = 0; i < 6; i++)
        {
            snprintf(res + i * 3, 4, "%02x:", 0xff & mac[i]);
        }
        res[17] = 0;
        return res;
    }

    /**
     * @brief Helper function for retracing the contents of the message buffer in case of errors
     *
     * @param buffer
     * @param buffersize
     * @param maxprintsize
     */
    void
    bufferprinthelper(char *buffer, uint32_t buffersize, uint32_t maxprintsize)
    {
        uint32_t len = maxprintsize;
        if (buffersize < len)
        {
            len = buffersize;
        }

        printf("\t\tNext %d bytes: ", len);
        for (int i = 0; i < len; i++)
        {
            printf("%02x ", (char)buffer[i]);
        }
        printf("\n");
        fflush(stdout);
    }

    TypeId
    LApplication::GetTypeId()
    {
        static TypeId tid =
            TypeId("ns3::LApplication").AddConstructor<LApplication>().SetParent<Application>();
        return tid;
    }

    TypeId
    LApplication::GetInstanceTypeId() const
    {
        return LApplication::GetTypeId();
    }

    LApplication::LApplication()
    {
        NS_LOG_DEBUG("Create LApplication");
    }

    LApplication::~LApplication()
    {
        NS_LOG_DEBUG("Destruct LApplication");
    }

    void
    LApplication::StartApplication(void)
    {
        NS_LOG_DEBUG("Start Lowcaf Application");

        if (this->LType == Source)
        {
            // Schedule data content checking from the Lowcaf framework
            for (int i = 0; i < (int)m_stopTime.GetMilliSeconds(); i++)
            {
                Simulator::Schedule(MilliSeconds(i), &LApplication::LListenForServerData, this);
            }
        }
        InitLServerCommunication();
    }

    void
    LApplication::StopApplication(void)
    {
        NS_LOG_DEBUG("Stop LApplication");
        if (LType == Sink || LType == Intermediate)
        {
            if (ClientSocket >= 0)
            {
                NS_LOG_INFO("Sending End of Processing");
                // Send EndOfProcessing
                char endofprocessing = END_OF_SIM_CMD;
                int sentbytes = send(ClientSocket, &endofprocessing, 1, 0);
                // Close Socket
                close(ClientSocket);
                ClientSocket = -1;
            }
        }
    }

    void
    LApplication::DoDispose(void)
    {
        NS_LOG_DEBUG("Dispose LApplication");
        Application::DoDispose();
    }

    void
    LApplication::InitializeSourceLApp(char *lserver,
                                       int lsport,
                                       u_int32_t mynodeid,
                                       u_int32_t lnodeid,
                                       Ptr<NetDevice> outgoing)
    {
        Initialize(lserver, lsport, mynodeid, lnodeid, Source, NULL, outgoing);
    }

    void
    LApplication::InitializeIntermediateLApp(char *lserver,
                                             int lsport,
                                             u_int32_t mynodeid,
                                             u_int32_t lnodeid,
                                             Ptr<NetDevice> incoming,
                                             Ptr<NetDevice> outgoing)
    {
        Initialize(lserver, lsport, mynodeid, lnodeid, Intermediate, incoming, outgoing);
    }

    /**
     * @brief Initialize the Lowcaf application as Sink
     *
     */
    void
    LApplication::InitializeSinkLApp(char *lserver,
                                     int lsport,
                                     u_int32_t mynodeid,
                                     u_int32_t lnodeid,
                                     Ptr<NetDevice> incoming)
    {
        Initialize(lserver, lsport, mynodeid, lnodeid, Sink, incoming, NULL);
    }

    /**
     * @brief Initialize the Lowcaf application
     *
     */
    void
    LApplication::Initialize(char *lserver,
                             int lsport,
                             u_int32_t mynodeid,
                             u_int32_t lnodeid,
                             LApplicationType type,
                             Ptr<NetDevice> incoming,
                             Ptr<NetDevice> outgoing)
    {
        NS_LOG_INFO("Setting up Lowcaf Application");

        LServerAddr = lserver;
        LServerPort = lsport;
        LType = type;

        // LAID = NodeID
        LApplicationID = mynodeid; // GetNode()->GetId();
        NS_LOG_INFO("Setting Lowcaf App-ID = " << LApplicationID);

        // Set Incoming and outgoing NetDevs
        NDIncoming = incoming;
        NS_LOG_INFO("Set incoming interface = " << NDIncoming);

        NDOutgoing = outgoing;
        NS_LOG_INFO("Set outgoing interface = " << NDOutgoing);

        LNodeID = lnodeid;
        NS_LOG_INFO("Setting Lowcaf node ID = " << LNodeID);

        // Start Server, Listening for Packets
        // Init Callback for Nodes that are NOT Sources
        switch (LType)
        {
        case Source:
            /* code */
            break;
        case Intermediate:
            incoming->SetPromiscReceiveCallback(MakeCallback(&LApplication::LDispatchPacket, this));

            break;
        case Sink:
            incoming->SetPromiscReceiveCallback(MakeCallback(&LApplication::LDispatchPacket, this));

            break;

        default:
            NS_LOG_ERROR("Could not initialize Lowcaf client: App-Type not clear");
            exit(0);
            break;
        }
    }

    void
    LApplication::LListenForServerData()
    {
        if (!commactive)
        {
            return;
        }

        // Check whether Socket is broken
        int error = 0;
        socklen_t len = sizeof(error);
        int retval = getsockopt(ClientSocket, SOL_SOCKET, SO_ERROR, &error, &len);

        if (ClientSocket < 0 || error != 0 || retval != 0)
        {
            NS_LOG_ERROR("Connection to Lowcaf Server seems broken!");
            exit(1);
        }

        struct timeval timeout;
        timeout.tv_usec = 0.0;
        fd_set rfds;

        FD_ZERO(&rfds);
        FD_SET(ClientSocket, &rfds);
        int ret = select(ClientSocket + 1, &rfds, NULL, NULL, &timeout);

        // Check if data available. If not, return
        if (ret <= 0)
        {
            return;
        }

        NS_LOG_INFO("Got new data from Lowcaf Server");

        char messagebuf[MAX_PACKET_SIZE];
        int rcvlen;
        char command;

        // Do receive
        rcvlen = recv(ClientSocket, messagebuf, MAX_PACKET_SIZE, 0);

        if (rcvlen > 0)
        {
            NS_LOG_DEBUG("Received " << rcvlen << " bytes from Lowcaf Server");

            // Got nonempty data, push onto queue
            memcpy(LServerCommBuffer + LServerCommBufferLen, messagebuf, rcvlen);
            LServerCommBufferLen = LServerCommBufferLen + rcvlen; // update len
            NS_LOG_DEBUG("Receive Queue Len is " << LServerCommBufferLen);

            while (1)
            {
                // No more data
                if (LServerCommBufferLen == 0)
                {
                    break;
                }

                command = LServerCommBuffer[0];
                NS_LOG_INFO("Got message with command=" << (int)command);

                if (command == PACKET_CMD)
                {
                    try
                    {
                        while (!LProcessRcvPacket())
                        {
                            NS_LOG_DEBUG("Processing another Packet...");
                        }
                        NS_LOG_DEBUG("Processing done, Buffer Size is " << LServerCommBufferLen);
                    }
                    catch (const char *msg)
                    {
                        NS_LOG_WARN("Error interpreting received data: " << msg);
                    }
                    continue;
                }

                if (command == END_OF_SIM_CMD)
                {
                    // Received END-OF-SIM-Signal: Shutdown Socket and schedule all received events
                    NS_LOG_INFO("Received End of Sim: Shutting down");
                    shutdown(ClientSocket, SHUT_RDWR);
                    close(ClientSocket);

                    commactive = false;
                }
                else if (command == CURRENTLY_NO_DATA)
                {
                    NS_LOG_DEBUG("Received NOP: Stop Listening for now");
                }
                else
                {

                    NS_LOG_ERROR("ERROR: Did not recognize command!");
                    // Print first 30 bytes in message buffer
                    bufferprinthelper(LServerCommBuffer, LServerCommBufferLen, 30);
                }
            }
        }
        else if (rcvlen < 0)
        {
            NS_LOG_ERROR("Connection to Lowcaf Server seems broken!");
        }
    }

    int
    LApplication::LProcessRcvPacket()
    {
        char *dstmac;
        Mac48Address destinationmac = Mac48Address();
        u_int16_t prototype;
        u_int64_t delay;
        u_int32_t pktlen;
        u_int8_t *pktdata;

        // The message must at least contain the fixed length fields
        if (LServerCommBufferLen < CMD_SIZE + DELAY_SIZE + PROTO_TYPE_SIZE + PKT_LEN_SIZE)
        {
            NS_LOG_DEBUG("Packet too small for processing, need at least "
                         << CMD_SIZE + DELAY_SIZE + PROTO_TYPE_SIZE + PKT_LEN_SIZE << " Bytes");
            return -1;
        }

        if (LServerCommBuffer[0] != PACKET_CMD)
        {
            NS_LOG_DEBUG("Next Packet has different command=" << LServerCommBuffer[0]
                                                              << ". Stop Processing.");
            bufferprinthelper(LServerCommBuffer, LServerCommBufferLen, 30);
            return -1;
        }

        memcpy(&delay, LServerCommBuffer + CMD_SIZE, DELAY_SIZE);
        memcpy(&pktlen, LServerCommBuffer + CMD_SIZE + DELAY_SIZE + PROTO_TYPE_SIZE, PKT_LEN_SIZE);

        pktdata = (u_int8_t *)LServerCommBuffer + CMD_SIZE + DELAY_SIZE + PROTO_TYPE_SIZE + PKT_LEN_SIZE;

        // Get Dst-Mac
        dstmac = mac48tostr(pktdata);
        destinationmac = Mac48Address(dstmac);

        // Get Ethertype
        memcpy(&prototype, pktdata + ETH_MAC_SIZE * 2, ETH_PROTO_TYPE_SIZE);

        // Not enough data to process next packet
        if (CMD_SIZE + DELAY_SIZE + PROTO_TYPE_SIZE + PKT_LEN_SIZE + ntohl(pktlen) >
            LServerCommBufferLen)
        {
            NS_LOG_DEBUG("Packet data seems to be incomplete yet");
            return -1;
        }

        NS_LOG_DEBUG("\tDelay: " << htobe64(delay));
        NS_LOG_DEBUG("\tDst-MAC: " << dstmac);
        NS_LOG_DEBUG("\tProtocol type: " << ntohs(prototype));
        NS_LOG_DEBUG("\tPacket length: " << ntohl(pktlen));
        NS_LOG_INFO("Got Packet with Delay=" << htobe64(delay) << ", Destination=" << destinationmac);

        // Create packet without ethernet header
        Ptr<Packet> pktptr = Create<Packet>(pktdata + ETH_HEADER_SIZE, ntohl(pktlen) - ETH_HEADER_SIZE);

        // SCHEDULE PACKET
        NS_LOG_DEBUG("Scheduling packet");
        Simulator::Schedule(
            MicroSeconds(htobe64(delay)),
            MakeCallback(&LApplication::LSendPacket, this, pktptr, destinationmac, ntohs(prototype)));

        NS_LOG_DEBUG("Scheduling successful");

        // Remove packet from buffer and set its Len new
        int packetsize = CMD_SIZE + DELAY_SIZE + PROTO_TYPE_SIZE + PKT_LEN_SIZE + ntohl(pktlen);
        memcpy(LServerCommBuffer, LServerCommBuffer + packetsize, LServerCommBufferLen - packetsize);
        LServerCommBufferLen = LServerCommBufferLen - packetsize;

        return 0;
    }

    void
    LApplication::InitLServerCommunication()
    {
        NS_LOG_INFO("Lowcaf Server is on " << LServerAddr << ":" << LServerPort);

        ClientSocket = socket(AF_INET, SOCK_STREAM, 0);
        if (ClientSocket < 0)
        {
            NS_LOG_ERROR("Error setting up Lowcaf client");
            exit(1);
        }

        int keepalive = 1;
        if (setsockopt(ClientSocket, SOL_SOCKET, SO_KEEPALIVE, &keepalive, sizeof(keepalive)) < 0)
        {
            NS_LOG_ERROR("Error setting up Lowcaf client: Could not set KEEPALIVE");
            exit(1);
        }

        struct sockaddr_in clientaddr;

        memset(&clientaddr, 0, sizeof(clientaddr));

        clientaddr.sin_family = AF_INET;
        clientaddr.sin_addr.s_addr = inet_addr(LServerAddr);
        clientaddr.sin_port = htons(LServerPort);

        while (connect(ClientSocket, (sockaddr *)&clientaddr, sizeof(clientaddr)) < 0)
        {
            NS_LOG_WARN("Could not connect to Lowcaf Server");
            sleep(5);
        }
        LServerCommBufferLen = 0;
        commactive = true;
        NS_LOG_INFO("Connected to Lowcaf Server");
    }

    /**
     * @brief Forward a packet coming from the incoming interface to the Lowcaf Server. Assumes an
     * initial Delay of 0
     *
     * @param packet
     */
    void
    LApplication::LDispatchPacket(Ptr<NetDevice> netdev, Ptr<Packet> packet)
    {
        NS_LOG_DEBUG("Got packet");

        // NS_LOG_DEBUG("Packet received");
        if (ClientSocket < 0)
        {
            NS_LOG_ERROR("Connection to Lowcaf Server seems broken!");
        }

        u_int8_t serializedpacket[MAX_PACKET_SIZE];
        u_int32_t packetsize = packet->CopyData(serializedpacket, MAX_PACKET_SIZE);
        if (packetsize <= 0)
        {
            NS_LOG_WARN("Serialized Packet has no size or failed serializing");
            return;
        }

        u_int8_t *buffer;
        buffer = (u_int8_t *)malloc(CMD_SIZE + HOST_SIZE + LNODE_SIZE + DELAY_SIZE + PKT_LEN_SIZE +
                                    packetsize);

        u_int16_t cmd = PACKET_CMD;

        u_int64_t initdelay = 0;

        u_int32_t nlappid = htonl(LApplicationID);
        u_int32_t nlnodeid = htonl(LNodeID);
        u_int64_t ndelay = htobe64(initdelay);
        u_int32_t npacketsize = htonl(packetsize);

        memcpy(buffer, &cmd, CMD_SIZE);
        memcpy(buffer + CMD_SIZE, &nlappid, HOST_SIZE);
        memcpy(buffer + CMD_SIZE + HOST_SIZE, &nlnodeid, LNODE_SIZE);
        memcpy(buffer + CMD_SIZE + HOST_SIZE + LNODE_SIZE, &ndelay, DELAY_SIZE);
        memcpy(buffer + CMD_SIZE + HOST_SIZE + LNODE_SIZE + DELAY_SIZE, &npacketsize, PKT_LEN_SIZE);
        memcpy(buffer + CMD_SIZE + HOST_SIZE + LNODE_SIZE + DELAY_SIZE + PKT_LEN_SIZE,
               serializedpacket,
               packetsize);

        int sentbytes = send(ClientSocket,
                             buffer,
                             CMD_SIZE + HOST_SIZE + LNODE_SIZE + DELAY_SIZE + PKT_LEN_SIZE + packetsize,
                             0);

        if (sentbytes < 0)
        {
            NS_LOG_ERROR("Sending message to Lowcaf Server failed");
        }
        else
        {
            NS_LOG_DEBUG("Sent message with " << sentbytes << " bytes to Lowcaf Server");
        }
        LListenForServerData();
    }

    /**
     * @brief Send one distinct packet via the outgoing interface
     *
     * @param packet
     * @param dstaddr
     * @param prototype
     */
    void
    LApplication::LSendPacket(Ptr<Packet> packet, Mac48Address dstaddr, u_int16_t prototype)
    {
        NS_LOG_DEBUG("Sending on interface NDOutgoint with MAC " << NDOutgoing->GetAddress());
        NDOutgoing->Send(packet, dstaddr, prototype);
        NS_LOG_DEBUG("Packet Sent!");
    }

} // namespace ns3
