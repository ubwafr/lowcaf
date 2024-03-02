import logging
import selectors
from multiprocessing.connection import Connection

from src.packetprocessing.bbsocket import BBSocket, EndOfDataError

LOGGER = logging.getLogger(__name__)

class ShutDownReceivedError(RuntimeError):
    pass


def socket_runner(bb_socks: list[BBSocket], cmd: Connection):
    """
    This function is responsible for relaying all communication between this
    application and external clients. This function should typically be
    spawned as a separate process because it will only return when all clients
    have disconnected

    Args:
        bb_socks: A list of all BBSockets for external connections
        cmd: A command channel for communication between the process
    """
    sel = selectors.DefaultSelector()

    # registering the command channel
    sel.register(cmd, selectors.EVENT_READ, (None, 'Terminate'))

    for bb_sock in bb_socks:
        LOGGER.debug(
            f'Selector: Registering Socket {bb_sock.sock.getsockname()}'
        )
        sel.register(bb_sock.sock,
                     selectors.EVENT_READ,
                     (bb_sock, bb_sock.accept, [sel, cmd]))

        # register all pipes
        node_id: int
        pipe_conn: Connection
        for node_id, pipe_conn in bb_sock.pipes.items():
            LOGGER.debug(
                f'Selector: Registering pipe to node {node_id}'
            )
            sel.register(pipe_conn,
                         selectors.EVENT_READ,
                         (bb_sock, bb_sock.process_outgoing, [pipe_conn]))

        # we allow exactly one connection
        bb_sock.sock.listen(1)

    try:
        # actual core loop
        while True:
            LOGGER.debug('Waiting on next batch of messages')
            exec_sel(sel)

    except ShutDownReceivedError:
        print('Terminating Socket Runner')

        for bb_sock in bb_socks:
            # can we guarantee that sockets are open at this point?
            # this is our fin
            print('Sending fin to all sockets')
            # todo: shutdown received
            if not bb_sock.is_terminated():
                bb_sock.conn.send(b'\x02')


def exec_sel(sel: selectors.BaseSelector):
    events = sel.select()
    LOGGER.debug(f'Received {len(events)} events')
    for key, mask in events:
        if key.data == (None, 'Terminate'):
            print("--------------------------------------why")
            raise ShutDownReceivedError

        print(key.data)
        bbsock: BBSocket = key.data[0]
        callback = key.data[1]

        # print('running')

        if callback is None:
            print("--------------------------------------why")
            raise ShutDownReceivedError

        # todo: for some reason the bbsock can be None, maybe we skip this
        #  case completely
        if bbsock is None:
            continue
        if not bbsock.is_terminated():
            LOGGER.debug(f'{key.data[2]}')

        try:
            callback(*key.data[2])
        except EndOfDataError:
            # todo: if all sockets are EOD and I am exhausted then we need to
            #  initiate a stop here
            pass
        except ConnectionResetError:
            bbsock.cleanup(sel)


