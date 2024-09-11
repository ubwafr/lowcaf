import logging
import selectors
import socket
from multiprocessing.connection import Connection
from typing import Optional

from scapy.compat import raw
from scapy.layers.l2 import Ether

from lowcaf.packetprocessing.bbpacket import EODMsg, BBPacket, MsgSim2BB, \
    DecoderSim2BB, MsgBB2Sim

LOGGER = logging.getLogger(__name__)


class EndOfDataError(RuntimeError):
    def __init__(self, sock: 'BBSocket'):
        super().__init__()
        self.sock: 'BBSocket' = sock


class BBSocket:
    def __init__(self,
                 sock: socket.socket,
                 node_id: int,
                 conn: Connection):
        self.sock: socket.socket = sock

        # if conn is present then this socket is connected
        self.conn: Optional[socket.socket] = None
        self.conn_in_buff: bytes = bytes()
        self.pipes: dict[int, Connection] = {node_id: conn}

        self._terminated = False

    def accept(
            self, sel: selectors.BaseSelector,
            cmd: Connection
    ):
        if self.conn is not None:
            raise RuntimeError('There is is already an active connection')

        conn, addr = self.sock.accept()
        LOGGER.info(f'Received Connection Request from {addr}')
        conn.setblocking(False)
        self.conn = conn

        LOGGER.debug(
            f'Selector: Registering client for {addr}'
        )
        sel.register(
            conn,
            selectors.EVENT_READ,
            (self, self.process_incoming, [sel]))

        cmd.send(('Connected', self.sock.getsockname()))

    def process_incoming(self, sel: selectors.BaseSelector):
        if self.is_terminated():
            return

        # todo: conn can be None here
        received = self.conn.recv(1000)  # Should be ready
        if not received:
            LOGGER.info("Received Data was None")
            raise ConnectionResetError

        data = self.conn_in_buff + received
        LOGGER.debug('Received Data from socket------------')
        msgs, rem = DecoderSim2BB.buff2msgs(data)
        self.conn_in_buff = rem

        for msg in msgs:
            match msg:
                case MsgSim2BB():
                    msg: MsgSim2BB

                    pkt = BBPacket(Ether(msg.data), msg.delay_ns)
                    self.pipes[msg.node_id].send(pkt)
                case EODMsg():
                    for pipe in self.pipes.values():
                        pipe.send(msg)
                case _:
                    err_msg = f'Type {type(msg)} is not supported'
                    raise NotImplementedError(err_msg)

    def process_outgoing(self, pipe: Connection):
        if self._terminated:
            return

        LOGGER.debug("Transmitting scapy_pkt to NS3")
        pkt: BBPacket = pipe.recv()

        msg = MsgBB2Sim(10, raw(pkt.scapy_pkt), b'ab', b'ab')
        self.conn.sendall(msg.serialize())

    def is_terminated(self) -> bool:
        """
        Checks if this socket has already been terminated
        """
        return self._terminated

    def cleanup(self, sel: selectors.BaseSelector):
        self._terminated = True

        print('Client disconnected')
        sel.unregister(self.sock)
        self.conn = None
        self.sock.close()

        print('Indicating shutdown to all clients')
        for conn in self.pipes.values():
            sel.unregister(conn)

            conn.send(EODMsg())
            conn.close()
