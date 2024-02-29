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
#include "lapplicationtype.h"
#include "packetcontainer.h"

#include "ns3/application.h"
#include "ns3/core-module.h"
#include "ns3/network-module.h"

/*
 * @brief Some protocol field lengths
 *
 */
#define CMD_SIZE 1 // Command field size
#define HOST_SIZE 4 // Host field size
#define LNODE_SIZE 4 // LNode ID field size
#define DELAY_SIZE 8 // Delay field size
#define PROTO_TYPE_SIZE 2 // Protocol type field size
#define ETH_PROTO_TYPE_SIZE 2 // Ethernet Protocol type field size
#define ETH_MAC_SIZE 6 // MAC address field size
#define ETH_HEADER_SIZE 14 // Ethernet header size
#define PKT_LEN_SIZE 4 // Packet length field size
#define MAX_PACKET_SIZE 60000 // Maximum packet size

/**
 * @brief Different protocol commands
 *
 */
#define PACKET_CMD 1 // Command: New Packet
#define END_OF_SIM_CMD 2 // Command: End of simulation
#define CURRENTLY_NO_DATA 3 // Command: Currently no data available

using namespace ns3;

namespace ns3
{

  /**
   * @brief ns-3 application to allow a ns-3 Node to connect towards the Lowcaf framework. This allows the Node to receive packets from Lowcaf and send packets towards it
   *
   */
  class LApplication : public Application
  {
  public:
    LApplication();
    virtual ~LApplication();
    static TypeId GetTypeId();
    virtual TypeId GetInstanceTypeId() const;

    /**
     * @brief Initialize app as source nnode
     *
     * @param lserver Lowcaf framework server IP
     * @param lsport Lowcaf service port
     * @param mynodeid ID of my node (e.g. context ID)
     * @param lnodeid ID of node in the Lowcaf framework (not necessarily needed)
     * @param outgoing Outgoing network interface of an ns-3 node (NOT FROM LOWCAF)
     */
    void InitializeSourceLApp(char *lserver,
                              int lsport,
                              u_int32_t mynodeid,
                              u_int32_t lnodeid,
                              Ptr<NetDevice> outgoing);

    /**
     * @brief Initialize app as intermediate nnode. An intermediate node gets packets from a preceding node and sends them towards another node
     *
     * @param lserver Lowcaf framework server IP
     * @param lsport Lowcaf service port
     * @param mynodeid ID of my node (e.g. context ID)
     * @param lnodeid ID of node in the Lowcaf framework (not necessarily needed)
     * @param outgoing Outgoing network interface of an ns-3 node (NOT FROM LOWCAF)
     * @param incoming Incoming network interface of an ns-3 node (NOT TOWARDS LOWCAF)
     */
    void InitializeIntermediateLApp(char *lserver,
                                    int lsport,
                                    u_int32_t mynodeid,
                                    u_int32_t lnodeid,
                                    Ptr<NetDevice> incoming,
                                    Ptr<NetDevice> outgoing);

    /**
     * @brief Initialize app as sink nnode. A sink node only gets packets from a preceding node.
     *
     * @param lserver Lowcaf framework server IP
     * @param lsport Lowcaf service port
     * @param mynodeid ID of my node (e.g. context ID)
     * @param lnodeid ID of node in the Lowcaf framework (not necessarily needed)
     * @param incoming Incoming network interface of an ns-3 node (NOT TOWARDS LOWCAF)
     */
    void InitializeSinkLApp(char *lserver,
                            int lsport,
                            u_int32_t mynodeid,
                            u_int32_t lnodeid,
                            Ptr<NetDevice> incoming);

  protected:
    virtual void DoDispose(void);

  private:
    int ClientSocket;               // Socket towards Lowcaf framework
    Ptr<NetDevice> NDIncoming;      // Incoming interface
    Ptr<NetDevice> NDOutgoing;      // Outgoing interface
    LApplicationType LType;         // Type of this application: source, intermediate, sink
    u_int32_t LApplicationID;       // ID of this application
    u_int32_t LNodeID;              // ID of remote Lowcaf node
    char LServerCommBuffer[512000]; // Buffer for processing messages from the Lowcaf framework. Needed due to packet segmentation in TCP
    u_int32_t LServerCommBufferLen; // Current size of Buffer
    char *LServerAddr;              // Lowcaf server address
    int LServerPort;                // Lowcaf service port
    bool commactive;                // Flag whether the communication is still active

    /**
     * @brief Start the application
     *
     */
    virtual void StartApplication(void);

    /**
     * @brief Stop the application
     *
     */
    virtual void StopApplication(void);

    /**
     * @brief Generic initialization function. Not callable from other classes but only public initialization methods.
     *
     */
    void Initialize(char *lserver,
                    int lsport,
                    u_int32_t nodeid,
                    u_int32_t lnodeid,
                    LApplicationType type,
                    Ptr<NetDevice> incoming,
                    Ptr<NetDevice> outgoing);

    /**
     * @brief Dispatch packet towards Lowcaf framework
     *
     * @param netdev Send on this network device
     * @param packet Packet to send
     */
    void LDispatchPacket(Ptr<NetDevice> netdev, Ptr<Packet> packet);

    /**
     * @brief Listen for data from the lowcaf server
     *
     */
    void LListenForServerData();

    /**
     * @brief Send packet towards succeeding ns-3 nodes
     *
     * @param packet Packet to send
     * @param dstaddr Destination MAC address
     * @param prototype Ethernet protocol type
     */
    void LSendPacket(Ptr<Packet> packet, Mac48Address dstaddr, u_int16_t prototype);

    /**
     * @brief Processes a Lowcaf packet from the LServerBuffer. If no data is left
     * or the buffer does not contain the whole message, the function returns -1.
     * The function also removes the processed part from the buffer and sets
     * the LServerCommBufferLen to its new value
     *
     * @return int 0 on success, otherwise -1
     */
    int LProcessRcvPacket();

    /**
     * @brief Initialize communication towards Lowcaf framework
     * 
     */
    void InitLServerCommunication();
  };

} // namespace ns3
