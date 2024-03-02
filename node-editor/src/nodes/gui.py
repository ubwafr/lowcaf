from collections import deque

import dearpygui.dearpygui as dpg

from src.nodeeditor.nodebuilder import NodeBuilder
from src.nodes.ifaces.inode import INode
from src.packetprocessing.bbpacket import BBPacket
from src.nodes.ifaces.rnode import RNode


class GuiG(INode):

    def __init__(
            self,
            node_id: int
    ):
        self.data_y = deque([0] * 200, maxlen=200)
        self.data_x = deque(list(range(200)), maxlen=200)

        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Gui", show=False) as _id:
                with dpg.node_attribute() as self.in_attr:
                    with dpg.plot(label='RF Bytes via TX') as self.plot:
                        dpg.add_plot_legend()

                        dpg.add_plot_axis(
                            dpg.mvXAxis,
                            label='Observed x Packets ago')
                        self.y_axis = dpg.add_plot_axis(
                            dpg.mvYAxis,
                            label='Bytes Transmitted')

                        self.series = dpg.add_line_series(list(self.data_x),
                                                          list(self.data_y),
                                                          label='Bytes Tx',
                                                          parent=self.y_axis, )

        super().__init__(node_id,
                         _id, _staging_container_id,
                         [self.in_attr], [])

    @staticmethod
    def disp_name():
        return 'Time Series Gui'

    def _show(self, dpcm: int):
        dpg.set_item_width(self.plot, 10 * dpcm)
        dpg.set_item_height(self.plot, 5 * dpcm)

    def update(self, data: dict):
        print(data['pkts'])

        self.data_y.appendleft(data['pkts'])
        # self.data_y.append(data['pkts'])
        print(self.data_y)
        # self.data_y.append(scapy_pkt['pkts'])
        # print(self.data_y)
        dpg.set_value(self.series, [list(self.data_x), list(self.data_y)])


class GuiN(RNode):
    def __init__(
            self,
            node_id: int,
            inode: GuiG | None,
    ):
        assert isinstance(inode, GuiG | None)
        super().__init__(node_id, 1, 0, inode)

        self.inode: GuiG | None = inode

    @staticmethod
    def create_from_inode(inode: GuiG) -> 'RNode':
        assert isinstance(inode, GuiG)
        return GuiN(
            inode.node_id,
            inode,
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        pkt: BBPacket = inputs[0].popleft()

        if self.inode is not None:
            self.inode.update({'pkts': len(pkt.scapy_pkt)})

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) >= 1


NodeBuilder.register_node(GuiG, GuiN)

dpg.destroy_context()
