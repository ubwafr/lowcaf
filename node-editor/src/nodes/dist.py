import math
from abc import abstractmethod
from collections import deque

import dearpygui.dearpygui as dpg
import numpy as np

from src.nodeeditor.nodebuilder import NodeBuilder
from src.nodes.ifaces.inode import INode
from src.nodes.ifaces.rnode import RNode
from src.packetprocessing.bbpacket import BBPacket


def get_current_dist(func, lin_space) -> (list, list):
    res = []
    for i in lin_space:
        res.append(func(i))

    return lin_space, res


class RandDist:
    @abstractmethod
    def activate(self, parent):
        raise NotImplementedError

    @abstractmethod
    def draw_sample(self) -> float:
        raise NotImplementedError


class NormalDist(RandDist):
    def __init__(self):
        self.mu = 0  # mean
        self.sigma = 0.1  # standard deviation

        self.lin_space = np.linspace(-1, 1, 100)

    def activate(self, parent):
        x, y = get_current_dist(self.compute_normal, self.lin_space)
        with dpg.plot(label='Distribution', parent=parent) as self.plot:
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label='x')
            self.y_axis = dpg.add_plot_axis(dpg.mvYAxis, label='y')

            self.series = dpg.add_line_series(
                x, y,
                label='Distribution',
                parent=self.y_axis)

            dpg.add_drag_line(label="mean",
                              color=[255, 0, 0, 255],
                              default_value=self.mu,
                              callback=self.update_mu)
            dpg.add_drag_line(label="std deviation",
                              color=[0, 255, 0, 255],
                              default_value=self.sigma,
                              callback=self.update_sigma)

    def update_mu(self, sender):
        self.mu = dpg.get_value(sender)

        self.lin_space = np.linspace(self.mu - 1, self.mu + 1, 100)

        x, y = get_current_dist(self.compute_normal, self.lin_space)
        dpg.set_value(self.series, [x, y])

    def update_sigma(self, sender):
        self.sigma = dpg.get_value(sender)

        x, y = get_current_dist(self.compute_normal, self.lin_space)
        dpg.set_value(self.series, [x, y])

    def compute_normal(self, x: int):
        return (1 / (self.sigma * np.sqrt(2 * np.pi)) *
                np.exp(- (x - self.mu) ** 2 / (2 * self.sigma ** 2)))

    def draw_sample(self) -> float:
        return np.random.normal(self.mu, self.sigma)


class PoissonDist(RandDist):
    def __init__(self):
        self.lam = 1  # lambda

        self.lin_space = list(range(1, 100))

    def activate(self, parent):
        x, y = get_current_dist(self.compute_normal, self.lin_space)
        print(x)
        print(y)
        with dpg.plot(label='Distribution', parent=parent) as self.plot:
            dpg.add_plot_legend()
            dpg.add_plot_axis(dpg.mvXAxis, label='x')
            self.y_axis = dpg.add_plot_axis(dpg.mvYAxis, label='y')

            self.series = dpg.add_line_series(
                x, y,
                label='Distribution',
                parent=self.y_axis)

            dpg.add_drag_line(label="lam",
                              color=[255, 0, 0, 255],
                              default_value=self.lam,
                              callback=self.update_lam)

    def update_lam(self, sender):
        self.lam = dpg.get_value(sender)

        x, y = get_current_dist(self.compute_normal, self.lin_space)
        dpg.set_value(self.series, [x, y])

    def compute_normal(self, x: int):
        return (math.pow(self.lam, x) *
                math.pow(math.e, -self.lam)) / math.factorial(x)

    def draw_sample(self):
        return np.random.poisson(self.lam)


class DistG(INode):

    def __init__(
            self,
            node_id: int
    ):
        self.outputs = []

        self.dist: RandDist = NormalDist()
        self.dpcm = None

        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Dist", show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Input
                ) as self.in_attr:
                    self.dist_sel = dpg.add_combo(
                        ['Normal', 'Poisson'],
                        default_value='Normal',
                        callback=self.change_dist,
                    )
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr:
                    dpg.add_text('Output')

        super().__init__(
            node_id,
            _id,
            _staging_container_id,
            [self.in_attr],
            [self.out_attr])

        self.dist.activate(self.in_attr)

    def change_dist(self):
        dpg.delete_item(self.dist.plot)

        tgt_dist = dpg.get_value(self.dist_sel)

        if tgt_dist == 'Normal':
            self.dist = NormalDist()
        elif tgt_dist == 'Poisson':
            self.dist = PoissonDist()
        else:
            raise ValueError

        self.dist.activate(self.in_attr)

        if self.dpcm is not None:
            self.show(self.dpcm)

    @staticmethod
    def disp_name():
        return 'Distribution'

    def _show(self, dpcm: int):
        self.dpcm = dpcm

        dpg.set_item_width(self.dist.plot, 10 * self.dpcm)
        dpg.set_item_height(self.dist.plot, 5 * self.dpcm)

        dpg.set_item_width(self.dist_sel, 10 * self.dpcm)


class DistN(RNode):

    def __init__(
            self,
            node_id: int,
            inode: DistG | None,
            dist: RandDist
    ):
        super().__init__(node_id, 1, 1, inode)
        self.dist = dist

    @staticmethod
    def create_from_inode(inode: DistG) -> 'RNode':
        assert isinstance(inode, DistG)
        return DistN(
            inode.node_id,
            inode,
            inode.dist
        )

    def process(
            self,
            inputs: list[deque[BBPacket]],
            outputs: list[list[BBPacket]]):
        pkt: BBPacket = inputs[0].popleft()

        time_shift: float = self.dist.draw_sample()
        print('-----------')
        print(pkt.scapy_pkt.time)
        print(time_shift)
        pkt.scapy_pkt.time += max(time_shift, 0)
        print(pkt.scapy_pkt.time)
        print('-----------')
        print(f'--Dist: forwarded Pkt {pkt}--')
        outputs[0].append(pkt)

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) >= 1


NodeBuilder.register_node(DistG, DistN)
