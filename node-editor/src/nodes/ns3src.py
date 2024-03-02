import socket
from collections import deque
from multiprocessing.connection import Connection
from typing import Callable, Optional

import dearpygui.dearpygui as dpg

from src.nodeeditor.nodebuilder import NodeBuilder
from src.nodes.ifaces.inode import INode
from src.nodes.ifaces.rnode import RNode
from src.nodes.jgf.jnode import JNode
from src.packetprocessing.bbpacket import BBPacket, EODMsg


class NS3SrcG(INode):

    def __init__(
            self,
            node_id: int,
    ):
        self.conn: Optional[Connection] = None
        self.ready: bool = False

        with dpg.stage() as _staging_container_id:
            with dpg.node(label=self.disp_name(), show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr:
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

        super().__init__(
            node_id, _id, _staging_container_id, [], [self.out_attr])

    @staticmethod
    def disp_name():
        return 'NS3 Source'

    def _show(self, dpcm: int):
        self.dpcm = dpcm

        dpg.set_item_width(self.contents, 3 * self.dpcm)



    def _add_meta_data_out_attr(self, idx: int) -> dict | None:
        if idx == 0:
            return {
                'ip': dpg.get_value(self.address),
                'port': dpg.get_value(self.port)
            }
        else:
            raise ValueError(f'{self.disp_name()} has only one output')

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):
        out = out_attrs[0].add_metadata
        dpg.set_value(self.address, out['ip'])
        dpg.set_value(self.port, out['port'])

    def set_addr_port(self, address: str, port: int):
        ip = list(socket.inet_aton(address))
        dpg.set_value(self.address, ip)
        dpg.set_value(self.port, port)

    def int4_to_ip(self) -> str:
        a, b, c, d = dpg.get_value(self.address)
        return f'{a}.{b}.{c}.{d}'


class NS3SrcN(RNode):
    def __init__(
            self,
            node_id: int,
            address: str,
            port: int,
            inode: NS3SrcG | None = None
    ):
        super().__init__(node_id, 0, 1, inode)

        assert isinstance(inode, NS3SrcG | None)
        self.inode: NS3SrcG | None = inode

        assert isinstance(address, str)
        assert isinstance(port, int)

        self.address: str = address
        self.port: int = port

        self.conn: Optional[Connection] = None
        self.ready: bool = False

    @staticmethod
    def create_from_inode(inode: NS3SrcG) -> 'RNode':
        assert isinstance(inode, NS3SrcG)
        return NS3SrcN(
            inode.node_id,
            inode.int4_to_ip(),
            dpg.get_value(inode.port),
            inode
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        """
        A src has no inputs and thus we don't use them.
        """
        if not self.conn.poll():
            # Because we always signal ready to not stop the simulation, there
            # is the possibility that NS3 has not yet made scapy_pkt available to us
            # alternatively we could differentiate between being really
            # ready and just not having scapy_pkt at the moment
            return

        ret = self.conn.recv()
        if isinstance(ret, EODMsg):
            print('Node State changed')
            self.ready = False
        elif isinstance(ret, BBPacket):

            pkt = ret

            print(f'--NS3 Source: sent Pkt {pkt}--')
            outputs[0].append(pkt)
        else:
            raise NotImplementedError(
                f'Type {type(ret)} is unsupported: {ret}')

    def is_ready(self, inputs: list[deque]) -> bool:
        return self.ready

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        self.conn = reg_socks(
            self.address,
            self.port,
            self.id)
        self.ready = True


NodeBuilder.register_node(NS3SrcG, NS3SrcN)

