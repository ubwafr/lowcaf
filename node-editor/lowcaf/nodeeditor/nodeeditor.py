import importlib
import importlib.resources as res
import json
import pkgutil
import socket
import warnings
from collections import defaultdict
from multiprocessing import Process, Queue
from queue import Empty
from typing import Type

import dearpygui.dearpygui as dpg

import resources.fonts
import lowcaf.nodes
from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodeeditor.nodemanager import NodeManager
from lowcaf.nodeeditor.portid import PortID
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.nodes.jgf.jedge import JEdge
from lowcaf.nodes.jgf.jfgkeys import JNODE_ATTR_TYPE, JEDGE_REL_ATTR2
from lowcaf.nodes.jgf.jnode import JNode
from lowcaf.packetprocessing.packetprocessor import PacketProcessor

for x in pkgutil.iter_modules(lowcaf.nodes.__path__):
    print(x.name)
    importlib.import_module(f'.{x.name}', 'lowcaf.nodes')

# from screeninfo import get_monitors

dpg.create_context()

NODE_EDITOR = 'node_editor'


def cancel():
    """
    For a reason unknown to me we must define the cancel call back as module
    level function.

    All other positions and even lambda functions seem to cause segfaults
    """
    pass


class NodeEditor:

    def __init__(self):
        # load default font
        files = res.files(resources.fonts)
        print(files)
        font = files.joinpath('Ubuntu-R.ttf')

        self.dpcm = 60

        print(self.dpcm)
        with dpg.font_registry():
            self._default_font = dpg.add_font(str(font), int(0.4 *
                                                             self.dpcm))
        self.build_main_window()
        self.node_links = set()

        self.node_mngr = NodeManager()

        # self.nodes: dict[int, INode] = {}

        # queue for communication with UDP server
        self.q = Queue()

        # the process of the UDP server
        self.rx_proc = None

        with dpg.handler_registry() as self.key_input_reg:
            dpg.add_key_release_handler(key=dpg.mvKey_A,
                                        callback=self.right_click_cb,
                                        tag='click_handler')

        # dpg.hide_item(self.key_input_reg)

        self.build_right_click_menu()

        with dpg.file_dialog(
                directory_selector=False,
                show=False,
                callback=self.import_nodes_jgf_cb,
                height=8 * self.dpcm,
                width=14 * self.dpcm,
                cancel_callback=cancel
        ) as self.f_dialog:
            dpg.add_file_extension(".*")

        with dpg.item_handler_registry(tag='node_handler'):
            # todo: could this be moved into the nodeeditor?
            dpg.add_item_clicked_handler(button=dpg.mvMouseButton_Right,
                                         callback=self.node_right_clicked)
            # dpg.add_item_hover_handler(callback=self.test)

    @staticmethod
    def run_udp_receiver(q):

        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(('127.0.0.1', 12000))
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        port = server_socket.getsockname()[1]

        print(f'UDP server listening on port {port}')

        while True:
            message, address = server_socket.recvfrom(1024)
            print(message)
            message = json.loads(message.decode('utf-8'))
            q.put_nowait(message)

    def check_id_already_connected_to(
            self,
            attr_id,
            start: bool
    ) -> None | str | int:
        if start:
            attr = 'attr_1'
        else:
            attr = 'attr_2'

        for link in self.node_links:
            point = dpg.get_item_configuration(link)[attr]
            if point == attr_id:
                return link
        else:
            return None

    def start(self):
        dpg.create_viewport(title='Belligerent Blob', width=20 * self.dpcm,
                            height=10 * self.dpcm)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        dpg.set_primary_window(self.main_window, True)

        while dpg.is_dearpygui_running():
            try:
                data = self.q.get_nowait()
                print(data)

                node_id = int(data['node_id'])

                try:
                    self.node_mngr.get_node_id(node_id).update(data)
                except KeyError:
                    warnings.warn(f'No node with ID {node_id}')
            except Empty:
                pass

            dpg.render_dearpygui_frame()
        # dpg.start_dearpygui()
        print('Terminated Application')
        dpg.destroy_context()

    def link(self,
             start: int | str,
             end: int | str,
             parent=NODE_EDITOR) -> int | str:
        """
        Add a link between two attributes.

        If there is another link to the target, the other link will be removed

        Args:
            start: ID of the start attribute
            end: ID of the end attribute
            parent: ID of the parent

        Returns:
            ID of the created link
        """

        def check_remove_lnk(link):
            if link is not None:
                dpg.delete_item(link)
                self.node_links.remove(link)

        s = self.check_id_already_connected_to(start, start=True)
        e = self.check_id_already_connected_to(end, start=False)
        check_remove_lnk(s)
        check_remove_lnk(e)

        # a node link also has an ID!!
        lnk = dpg.add_node_link(start, end, parent=parent,
                                user_data=self)
        self.node_links.add(lnk)

        return lnk

    def remove_node(self, dpg_id: int):
        """
        Completely and safely removes a node

        This function also takes care of links to this node
        """
        print("Remove Node was called")
        print(self)
        print(dpg_id)

        self.node_mngr.rem_dpg(dpg_id)
        # del self.nodes[node_id]

        lnks = dpg.get_item_children(self.node_editor, 0)
        attrs = dpg.get_item_children(dpg_id, 1)

        for lnk in lnks:
            lnk_conf = dpg.get_item_configuration(lnk)
            for attr in attrs:

                if lnk_conf['attr_2'] == attr or lnk_conf['attr_1'] == attr:
                    nodeeditor = dpg.get_item_user_data(lnk)
                    nodeeditor.delink_cb(nodeeditor, lnk)

        dpg.configure_item(dpg_id, show=False)
        dpg.delete_item(dpg_id)

    # callback runs when user attempts to connect attributes
    def link_cb(self, sender, app_data):
        # app_data -> (link_id1, link_id2)
        # sender is the nodeeditor

        self.link(app_data[0], app_data[1], parent=sender)

    # callback runs when user attempts to disconnect attributes
    def delink_cb(self, sender, app_data):
        # app_data -> link_id
        dpg.delete_item(app_data)
        self.node_links.remove(app_data)
        print('delink called')

    def right_click_cb(self, sender, app_data):
        """
        Displays the right-click menu for adding new nodes when not already
        displayed. If already displayed, hides the menu again.

        Args:
            sender: norm
            app_data: norm
        """
        if dpg.is_key_down(dpg.mvKey_Control):
            print(f"sender is: {sender}")
            print(f"app_data is: {app_data}")

            config = dpg.get_item_configuration('right_click_menu')
            # if True:
            if not config['show']:
                dpg.configure_item("right_click_menu", show=True,
                                   pos=dpg.get_mouse_pos(local=False))
            else:
                dpg.configure_item("right_click_menu", show=False)

    def add_n_show(self,
                   node: INode,
                   parent: int | str,
                   pos: list[int] | None = None) -> str | int:
        node.submit(parent)
        self.node_mngr.add_node(node)
        # self.nodes[node.dpg_id] = node
        node.show(self.dpcm, pos)
        return node.dpg_id

    def add_node_cb(self, sender, app_data, userdata):
        selected = dpg.get_value(userdata)
        pos = dpg.get_item_pos('right_click_menu')

        try:
            const: Type[INode] = NodeBuilder.get_name_inode_dict()[selected]
            node_id = self.node_mngr.get_free_node_id()
            self.add_n_show(const(node_id), NODE_EDITOR, pos)
        except KeyError:
            raise ValueError(f'{selected} is not in the list of supported '
                             f'nodes')
        dpg.configure_item("right_click_menu", show=False)

    def run_pp_cb(self, sender, app_data):
        """
        Export nodes to the packet processor
        """
        with dpg.window(label="Simulation State", modal=True, show=True,
                        autosize=True) as runner:
            txt = dpg.add_text("Loading")
            dpg.add_separator()
            loader = dpg.add_progress_bar(label='Loading', width=5 * self.dpcm)
            running = dpg.add_loading_indicator(show=False)

        # split frame is necessary, because the window will only be drawn in
        # the next frame if I understand correctly
        dpg.split_frame()
        width = dpg.get_item_width(self.main_window) // 2
        height = dpg.get_item_height(self.main_window) // 2
        width_popup = dpg.get_item_width(runner) // 2
        height_popup = dpg.get_item_height(runner) // 2

        print((width, height))
        print((width_popup, height_popup))

        pos = [width - width_popup, height - height_popup]
        dpg.set_item_pos(runner, pos)

        dpg.set_value(txt, 'Building edge database ...')
        edges_db = {}

        for link in self.node_links:
            conf = dpg.get_item_configuration(link)
            edges_db[conf['attr_1']] = conf['attr_2']

        dpg.set_value(txt, 'Building port mappings ...')
        dpg.set_value(loader, 0.2)
        pos2dpg: dict[int, PortID] = {}
        for node_obj in self.node_mngr.values():
            for idx, node_id in enumerate(node_obj.inputs):
                pos2dpg[node_id] = PortID(node_obj.node_id, idx)

            for idx, node_id in enumerate(node_obj.outputs):
                pos2dpg[node_id] = PortID(node_obj.node_id, idx)

        dpg.set_value(txt, 'Building link database ...')
        dpg.set_value(loader, 0.4)
        links: dict[int, dict[int, PortID]] = {}
        for (node_id, _), node_obj in self.node_mngr.items():
            dat = {}
            for idx, out_node_id in enumerate(node_obj.outputs):
                dat[idx] = pos2dpg[edges_db[out_node_id]]

            links[node_id] = dat

        dpg.set_value(txt, 'Finished setup')
        dpg.set_value(loader, 0.6)

        node_d = NodeBuilder.convert_i2r_dict(self.node_mngr.cpy_node_id_dict())
        pp = PacketProcessor(node_d, links)

        dpg.configure_item(running, show=True)
        pp.drive()

        dpg.configure_item(running, show=False)
        dpg.set_value(loader, 1)
        dpg.set_value(txt, 'Simulation finished')

    def export_nodes_jgf_cb(self, sender, app_data):
        """
        Exports nodes to the JSON-Graph-Specification format.
        See: https://github.com/jsongraph/json-graph-specification
        """

        data_db = {
            'graph': {
                'directed': True,
                'metadata': {
                    'dpcm': self.dpcm
                },
                'nodes': {},
                'edges': []
            }
        }

        edges_db = data_db['graph']['edges']
        nodes_db = data_db['graph']['nodes']

        for link in self.node_links:
            conf = dpg.get_item_configuration(link)
            start_attr = conf['attr_1']
            end_attr = conf['attr_2']
            print(conf)
            print(f'Link from {start_attr} -> {end_attr}')

            jedge = JEdge(start_attr, end_attr, JEDGE_REL_ATTR2)

            edges_db.append(jedge.to_jgf())

        node_obj: INode
        for node_obj in self.node_mngr.values():
            _nodes, _edges = node_obj.to_jgf()
            nodes_db |= _nodes
            edges_db.extend(_edges)

        with open(app_data['file_path_name'], 'w', encoding='utf-8') as writer:
            writer.write(json.dumps(data_db, indent=2))

        print(json.dumps(data_db, indent=2))

    def _show_file_sel(self,
                       callback,
                       file_extensions: list[str],
                       default: str = ''):
        children = dpg.get_item_children(self.f_dialog, 0)
        for child in children:
            dpg.delete_item(child)

        for ext in file_extensions:
            dpg.add_file_extension(ext, parent=self.f_dialog)
        dpg.configure_item(self.f_dialog, default_filename=default)
        dpg.set_item_callback(self.f_dialog, callback)
        dpg.show_item(self.f_dialog)

    def file_sel_jgf_export_cb(self, sender, app_data):
        self._show_file_sel(self.export_nodes_jgf_cb,
                            ['.jgf'],
                            'save')

    def file_sel_jgf_import_cb(self, sender, app_data):
        """
        Display a file selector allowing to select a jgf file
        """
        self._show_file_sel(self.import_nodes_jgf_cb,
                            ['.jgf'])

    def import_nodes_jgf_cb(self, sender, app_data):
        """
        Imports node scapy_pkt from a JGF file

        The import happens in several steps:
        1. Read json from jgf file
        2. Build edge list (all edges)
        3. Build forward and reverse edge dicts
        4. Find all nodes belonging to a "real" node (input attributes and
        output attributes)
        5. Build each node
        6. Add the remaining "real" edges
        """

        with open(app_data['file_path_name'], 'r', encoding='utf-8') as reader:
            data = reader.read()

        jgf = json.loads(data)
        nodes = jgf['graph']['nodes']
        old_dpcm = jgf['graph']['metadata']['dpcm']

        # each node_type should receive a list of nodes with corresponding
        # attributes

        edge_list = []
        forward: dict[int, list[int]] = defaultdict(list)
        reverse: dict[int, list[int]] = defaultdict(list)
        for edge in jgf['graph']['edges']:
            jedge = JEdge.from_jgf(edge)
            edge_list.append(jedge)

            forward[jedge.source].append(jedge.target)
            reverse[jedge.target].append(jedge.source)

        print('Forward and Reverse --------------------')
        print(forward)
        print(reverse)
        store = defaultdict(list)
        for node_id, node in jgf['graph']['nodes'].items():
            jnode = JNode.from_jgf(node)

            if jnode.node_type == JNODE_ATTR_TYPE:
                # we only look at "real" nodes
                continue

            in_attrs = [JNode.from_jgf(nodes[str(x)]) for x in reverse[
                jnode.node_id]]
            out_attrs = [JNode.from_jgf(nodes[str(x)]) for x in forward[
                jnode.node_id]]

            for el in in_attrs:
                if el in out_attrs:
                    raise ValueError(
                        f'Failure for {jnode.node_type}: Associated attr '
                        f'{el.node_id} appears as input and output. '
                        f'Suspected Reason: Invalid JGF')

            store[jnode.node_type].append({
                'jnode': jnode,
                'in_attrs': in_attrs,
                'out_attrs': out_attrs
            })

        print(store)

        id_mapping: dict[int, int] = dict()
        for node_type, stored in store.items():
            tmp = {x.type_name(): x for x in NodeBuilder.get_inode_cls()}
            cls = tmp[node_type]

            for node_data in stored:
                print(node_data)

                id_to_use: int
                jnode: JNode = node_data['jnode']
                if self.node_mngr.is_node_id_free(jnode.node_id):
                    id_to_use = jnode.node_id
                else:
                    id_to_use = self.node_mngr.get_free_node_id()
                    warnings.warn(f'Node ID {jnode.node_id} already in use. '
                                  f'Using {id_to_use} instead.')

                inode = cls(id_to_use)
                inode.from_jgf(
                    node_data['jnode'],
                    node_data['in_attrs'],
                    node_data['out_attrs'],
                    id_mapping)

                jnode = node_data['jnode']
                pos = jnode.position
                for val in pos:
                    int(val * (self.dpcm / old_dpcm))
                self.add_n_show(inode, NODE_EDITOR, pos)

        # finally connect the "real" edges
        for edge in edge_list:
            if edge.relation != JEDGE_REL_ATTR2:
                continue
            try:
                self.link(
                    id_mapping[edge.source],
                    id_mapping[edge.target],
                    NODE_EDITOR)
            except KeyError as e:
                key = int(str(e))

                print('Error Resolving')

                for node_t, node_lst in store.items():
                    for node_d in node_lst:
                        in_attrs: list[JNode] = node_d['in_attrs']
                        out_attrs: list[JNode] = node_d['out_attrs']

                        if key in [x.node_id for x in in_attrs]:
                            print(f'Missing key is related to type {node_t} '
                                  f'inputs')
                        if key in [x.node_id for x in out_attrs]:
                            print(f'Missing key is related to type {node_t} '
                                  f'outputs')
                raise e

        print(id_mapping)

    def start_server_cb(self, sender, app_data):
        if self.rx_proc is not None:
            self.rx_proc.kill()
        self.rx_proc = Process(target=NodeEditor.run_udp_receiver,
                               args=(self.q,),
                               daemon=True)

        self.rx_proc.start()

    def check_nodes_cb(self):
        print('Checking Nodes:')
        for node in NodeBuilder.get_inode_cls():
            print(node.type_name(), end=' ... ')
            test = node()
            print(test.disp_name(), end=' ... ')
            test.to_jgf()
            print('OK')

        print(f'BIT successful')

    def build_main_window(self):
        with dpg.window(label="BB", tag='BB') as self.main_window:
            dpg.bind_font(self._default_font)
            # b0 = dpg.add_button(label="Get all children",
            # callback=get_all_children)
            with dpg.menu_bar():
                with dpg.menu(label='File'):
                    dpg.add_menu_item(
                        label='Import Nodes',
                        callback=self.file_sel_jgf_import_cb)
                    dpg.add_spacer(height=self.dpcm // 8)
                    dpg.add_separator()
                    dpg.add_spacer(height=self.dpcm // 8)
                    dpg.add_menu_item(
                        label='Export Nodes',
                        callback=self.file_sel_jgf_export_cb)
                    dpg.add_spacer(height=self.dpcm // 8)
                    dpg.add_separator()
                    dpg.add_spacer(height=self.dpcm // 8)
                    dpg.add_menu_item(
                        label='Add Test Nodes',
                        callback=self.add_test_nodes_cb)
                    dpg.add_menu_item(
                        label='Run BBPacket Processor',
                        callback=self.run_pp_cb
                    )
                with dpg.menu(label='Server'):
                    dpg.add_menu_item(
                        label='Start UDP Server',
                        callback=self.start_server_cb
                    )
                with dpg.menu(label='BIT'):
                    dpg.add_menu_item(
                        label='Check Nodes',
                        callback=self.check_nodes_cb,
                    )
            with dpg.node_editor(
                    callback=self.link_cb,
                    delink_callback=self.delink_cb,
                    minimap=True,
                    minimap_location=dpg.mvNodeMiniMap_Location_BottomRight,
                    tag=NODE_EDITOR) as self.node_editor:
                pass

    def build_right_click_menu(self):
        with dpg.window(label="Right click window", modal=True, show=False,
                        id="right_click_menu", no_title_bar=True,
                        tag='right_click_menu'):
            dpg.add_text("Add Node")
            dpg.add_separator()
            combo = dpg.add_combo(
                list(NodeBuilder.get_name_inode_dict().keys()), width=0)
            with dpg.group(horizontal=True):
                dpg.add_button(label="OK", width=0,
                               callback=self.add_node_cb,
                               user_data=combo)
                dpg.add_button(label="Cancel", width=0,
                               callback=lambda: dpg.configure_item(
                                   "right_click_menu",
                                   show=False))

    def node_right_clicked(self, sender, appdata, userdata):
        print(sender)
        print(appdata)
        print(userdata)
        print('test')

        print(dpg.get_item_configuration(sender))
        # self.right_click_cb(None, None)

        # print(self.nodes)
        print(self.node_mngr.get_dpg(appdata[1]))
        node: INode = self.node_mngr.get_dpg(appdata[1])
        node.right_click_cb(self.remove_node)


if __name__ == '__main__':
    ne = NodeEditor()
    ne.start()
