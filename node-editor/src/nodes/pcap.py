from multiprocessing.connection import Connection

import dearpygui.dearpygui as dpg
from scapy.all import *

from src.nodeeditor.nodebuilder import NodeBuilder
from src.nodes.ifaces.inode import INode
from src.packetprocessing.bbpacket import BBPacket
from src.nodes.ifaces.rnode import RNode
from src.nodes.jgf.jnode import JNode

dpg.create_context()

LOGGER = logging.getLogger(__name__)

def cancel():
    pass


class PcapSourceG(INode):

    def __init__(
            self,
            node_id: int,
    ):
        self.text = None
        self.file_path: str | None = None
        self.reader: PcapReader | None = None
        self._ready = False

        # todo: Currently each PCAP source spawns its own file dialog which is
        #  probably wasteful. Instead one probably use one for all PcapSources
        #  and provide the tag as user scapy_pkt, or just by the sender
        with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.callback,
                cancel_callback=cancel,
                height=400,
                width=600,
        ) as f_dialog:
            dpg.add_file_extension(".*")
            self.f_dialog = f_dialog

        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Pcap Source", show=False) as _id:
                with dpg.node_attribute(
                        label="Node A2",
                        attribute_type=dpg.mvNode_Attr_Output) as self.att1:
                    self.text = dpg.add_button(
                        label="Select a file",
                        callback=lambda: dpg.show_item(self.f_dialog))

        super().__init__(
            node_id, _id, _staging_container_id, [], [self.att1])

    @staticmethod
    def disp_name():
        return 'Pcap Source'

    def callback(self, sender, app_data):
        for key, val in app_data['selections'].items():
            dpg.set_item_label(self.text, key)
            self.file_path = val

    def _add_meta_data_out_attr(self, idx: int) -> dict | None:
        if idx == 0:
            return {
                'text': dpg.get_item_label(self.text),
                'file_path': self.file_path
            }
        else:
            raise ValueError(f'{self.disp_name()} has only one input')

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):
        out = out_attrs[0]
        dpg.set_item_label(self.text, out.add_metadata['text'])
        self.file_path = out.add_metadata['file_path']


class PcapSourceN(RNode):
    def __init__(
            self,
            node_id: int,
            file_path: str,
            inode: PcapSourceG | None = None
    ):
        assert isinstance(inode, PcapSourceG | None)
        super().__init__(node_id, 0, 1, inode)

        self.inode: PcapSourceG | None = inode

        assert isinstance(file_path, str)
        self.file_path: str = file_path
        self.reader: PcapReader | None = None
        self._ready = False

    @staticmethod
    def create_from_inode(inode: PcapSourceG) -> 'RNode':
        assert isinstance(inode, PcapSourceG)
        return PcapSourceN(
            inode.node_id,
            inode.file_path,
            inode
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        try:
            LOGGER.debug("Read a packet")
            pkt = self.reader.read_packet()
            outputs[0].append(BBPacket(pkt, 0))
        except EOFError:
            LOGGER.info("PCAP is empty")
            self.reader.__exit__(None, None, None)
            self._ready = False

    def is_ready(self, inputs: list[deque]) -> bool:
        return self._ready

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        try:
            LOGGER.debug(f'Using path: {self.file_path}')
            self.reader: PcapReader = PcapReader(self.file_path).__enter__()
            self._ready = True
        except TypeError as err:
            raise RuntimeError(
                f'PCAP Source {self.id} has no file configured'
            ) from err


class PcapSinkG(INode):

    # todo: Currently each PCAP source spawns its own file dialog which is
    #  probably wasteful. Instead one probably use one for all PcapSources
    #  and provide the tag as user scapy_pkt, or just by the sender
    #  however, there is a strange bug(?) which prevents me from creating
    #  this dialoge as class parameter or outside it

    def __init__(
            self,
            node_id: int,
    ):
        self.text = None
        self.file_path: str | None = None
        self.writer: None | PcapWriter = None

        with dpg.file_dialog(
                directory_selector=False,
                show=False,
                default_filename='capture',
                callback=self.callback,
                cancel_callback=cancel,
                height=400,
                width=600,
        ) as self.f_dialog:
            dpg.add_file_extension(".pcap")

        with dpg.stage() as staging_container_id:
            with dpg.node(label="Pcap Sink", show=False) as node:
                with dpg.node_attribute(
                        label="Node A2",
                        attribute_type=dpg.mvNode_Attr_Input) as self.att1:
                    self.text = dpg.add_button(
                        label="Select a file",
                        callback=lambda: dpg.show_item(self.f_dialog))

        super().__init__(node_id, node, staging_container_id,
                         [self.att1], [])

    @staticmethod
    def disp_name():
        return 'Pcap Sink'

    def callback(self, sender, app_data):
        dpg.set_item_label(self.text, app_data['file_name'])
        self.file_path = app_data['file_path_name']

    def _add_meta_data_in_attr(self, idx: int) -> dict | None:
        if idx == 0:
            return {
                'text': dpg.get_item_label(self.text),
                'file_path': self.file_path
            }
        else:
            raise ValueError(f'{self.disp_name()} has only one input')

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):
        in_a = in_attrs[0]
        dpg.set_item_label(self.text, in_a.add_metadata['text'])
        self.file_path = in_a.add_metadata['file_path']


class PcapSinkN(RNode):

    def __init__(
            self,
            node_id: int,
            inode: PcapSinkG,
            file_path: str,
    ):
        assert isinstance(inode, PcapSinkG | None)
        super().__init__(node_id, 1, 0, inode)

        self.inode: PcapSinkG | None = inode

        self.file_path = file_path
        self.writer: None | PcapWriter = None

    @staticmethod
    def create_from_inode(inode: PcapSinkG) -> 'RNode':
        assert isinstance(inode, PcapSinkG)
        return PcapSinkN(
            inode.node_id,
            inode,
            inode.file_path
        )

    def process(
            self,
            inputs: list[deque[BBPacket]],
            outputs: list[list[BBPacket]]):
        pkt: BBPacket = inputs[0].popleft()

        LOGGER.debug(f"Writing a packet with time {pkt.scapy_pkt.time}")
        self.writer.write(pkt.scapy_pkt)
        # todo: Check what we actually mean with our timestamps

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) >= 1

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        try:
            self.writer = PcapWriter(self.file_path).__enter__()
        except TypeError as err:
            raise RuntimeError(
                f'PCAP Source {self.id} has no file configured'
            ) from err

    def teardown(self):
        self.writer.__exit__(None, None, None)


NodeBuilder.register_node(PcapSourceG, PcapSourceN)
NodeBuilder.register_node(PcapSinkG, PcapSinkN)
dpg.destroy_context()
