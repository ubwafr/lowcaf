"""
The PacketProcessor is the entity driving packets through the different
blocks. We use an external entity as this may allow us more complex
"""
import socket
import time
import logging

from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection

from lowcaf.packetprocessing.nodeselector import PrioritySelector
from lowcaf.packetprocessing.nodestate import NodeState
from lowcaf.nodeeditor.portid import PortID
from lowcaf.nodes.ifaces.rnode import RNode
from lowcaf.packetprocessing.bbsocket import BBSocket
from lowcaf.packetprocessing.msgdispatcher import socket_runner

LOGGER = logging.getLogger(__name__)


class PacketProcessor:
    def __init__(
            self,
            nodes: dict[int, RNode],
            links: dict[int, dict[int, PortID]]):

        self.nodes: dict[int, NodeState] = {}

        LOGGER.debug(f'Setting up {len(nodes)} nodes')
        for key, rnode in nodes.items():
            if not isinstance(rnode, RNode):
                raise ValueError(
                    f'Node {type(rnode)}:{rnode.id} is not an RNode'
                )
            self.nodes[key] = NodeState(rnode)

        self.links: dict[int, dict[int, PortID]] = links

        self.socks: list[BBSocket] = []

    @staticmethod
    def new_socket(
            ip_address: str,
            port: int
    ) -> socket.socket:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        LOGGER.info(f'Creating new socket: {ip_address}:{port}')
        server_socket.bind((ip_address, port))
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return server_socket

    def register_socket(self,
                        ip_address: str,
                        port: int,
                        node_id: int) -> Connection:

        pp_conn, node_conn = Pipe()

        for bbsock in self.socks:
            if bbsock.sock.getsockname() == (ip_address, port):
                LOGGER.info(f'Reusing existing socket for {ip_address}:{port}')
                bbsock.pipes[node_id] = pp_conn
                break
        else:
            # socket does not yet exist
            sock = self.new_socket(ip_address, port)
            bbsock = BBSocket(sock, node_id, pp_conn)
            self.socks.append(bbsock)

        return node_conn

    def viz_state(self):
        for node_state in self.nodes.values():
            print(node_state.viz())

    def setup(self):
        """
        Before calling drive, this function performs initial setup and
        configuration before the actual processing starts.
        """
        print("Setting Up Nodes ... ", end='')
        for node_state in self.nodes.values():
            node_state.node.setup(self.register_socket)
        print("OK")

    def drive(self):
        """
        This is the main function driving the simulation.

        TODO:
            Currently this may lead to some queues getting larger and
            larger. This could be the case if one path can continuously produce
            values while another path only occasionally produces a value. A
            potential fix would be to check the target inputs queue size before
            executing process
        """

        ps = PrioritySelector(self)

        if len(self.socks) > 0:
            print('Setup sockets ... ', end='')
            addrs = set([sock.sock.getsockname() for sock in self.socks])
            cmd, inner = Pipe()
            p = Process(target=socket_runner, args=(self.socks, inner))
            p.start()
            print('OK')

            print('Wait for NS3 sockets to come online ... ', end='')
            while len(addrs) > 0:
                command, val = cmd.recv()
                if command == 'Connected':
                    addrs.remove(val)
            print('OK')

            # don't touch self.socks from now on

            print('Running Simulation ... ', end='')
            self.sim_core(ps)
            print('FINISHED')

            print('Cleaning up ... ', end='')

            # wait a bit to allow all pipes/etc. to clear
            time.sleep(4)

            cmd.send('Terminate')
            p.join()
            print('OK')

        else:
            print('No sockets in graph. Running in offline mode')
            self.sim_core(ps)

        for node_state in self.nodes.values():
            node_state.node.teardown()

        # only touch the sockets after the process has joined again
        LOGGER.info('Tearing down')
        for bb_sock in self.socks:
            LOGGER.info(f'Cleanup socket: {bb_sock}')
            if bb_sock.conn is not None:
                bb_sock.conn.close()

            bb_sock.sock.close()

    def sim_core(self, ps):
        # main loop
        LOGGER.info('---------------SIM-CORE----------------')
        ps.gen_nodes(self)
