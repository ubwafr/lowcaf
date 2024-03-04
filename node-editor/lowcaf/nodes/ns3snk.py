import logging
import socket
from multiprocessing.connection import Connection
from typing import Optional, Callable

import dearpygui.dearpygui as dpg
from collections import deque

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.nodes.ifaces.rnode import RNode
from lowcaf.nodes.jgf.jnode import JNode

LOGGER = logging.getLogger(__name__)


class NS3SnkG(INode):

    def __init__(
            self,
            node_id: int
    ):
        self.conn: Optional[Connection] = None
        self.ready: bool = False

        with dpg.stage() as _staging_container_id:
            with dpg.node(label=self.disp_name(), show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Input
                ) as self.in_attr:
                    with dpg.group() as self.contents:
                        self.address = dpg.add_input_intx(
                            label='IP',
                            default_value=[127, 0, 0, 1],
                            min_value=0,
                            max_value=255,
                            min_clamped=True,
                            max_clamped=True,
                        )
                        self.port = dpg.add_input_int(
                            label='Port',
                            default_value=12000,
                            min_value=0,
                            max_value=2 ** 16 - 1,
                            min_clamped=True,
                            max_clamped=True,
                        )

        super().__init__(node_id, _id, _staging_container_id,
                         [self.in_attr], [])

    @staticmethod
    def disp_name():
        return 'NS3 Sink'

    def _show(self, dpcm: int):
        self.dpcm = dpcm

        dpg.set_item_width(self.contents, 3 * self.dpcm)

    def _add_meta_data_in_attr(self, idx: int) -> dict | None:
        if idx == 0:
            return {
                'ip': dpg.get_value(self.address),
                'port': dpg.get_value(self.port)
            }
        else:
            raise ValueError(f'{self.disp_name()} has only one input')

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):
        attr = in_attrs[0].add_metadata
        dpg.set_value(self.address, attr['ip'])
        dpg.set_value(self.port, attr['port'])

    def set_addr_port(self, address: str, port: int):
        ip = list(socket.inet_aton(address))
        dpg.set_value(self.address, ip)
        dpg.set_value(self.port, port)

    def int4_to_ip(self) -> str:
        a, b, c, d = dpg.get_value(self.address)
        return f'{a}.{b}.{c}.{d}'


class NS3SnkN(RNode):
    def __init__(
            self,
            node_id: int,
            address: str,
            port: int,
            inode: NS3SnkG | None = None,
    ):
        super().__init__(node_id, 1, 0, inode)

        assert isinstance(inode, NS3SnkG | None)
        self.inode: NS3SnkG | None = inode

        assert isinstance(address, str)
        assert isinstance(port, int)

        self.address: str = address
        self.port: int = port

        self.conn: Optional[Connection] = None
        self.ready: bool = False

    @staticmethod
    def create_from_inode(inode: NS3SnkG) -> 'RNode':
        assert isinstance(inode, NS3SnkG)
        return NS3SnkN(
            inode.node_id,
            inode.int4_to_ip(),
            dpg.get_value(inode.port),
            inode
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        pkt = inputs[0].popleft()

        LOGGER.debug(f'Received Pkt {pkt}')
        self.conn.send(pkt)

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) >= 1

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        self.conn = reg_socks(
            self.address,
            self.port,
            self.id)
        self.ready = True


NodeBuilder.register_node(NS3SnkG, NS3SnkN)
