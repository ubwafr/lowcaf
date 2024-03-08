from lowcaf.nodes.ifaces.inode import INode


class NodeManager:
    """
    The NodeManager associates INodes with the DPG IDs of the corresponding
    node windows. It makes them searchable in both directions, i.e., either
    by DPG ID or by the internal INode ID.

    The reason why the DPG ID is not the same as the INode ID is that the
    DPG ID needs to be globally unique, while the INode ID is only unique
    within a Plane/Node Editor Tab. The user may need the INode ID, e.g.,
    when sending data to a specific node from external sources and expects
    these IDs to be static, especially when loading a JGF file. The DPG IDs
    when not manually set are assigned in creation order of the nodes and
    need not correspond to the IDs that the nodes hat in a previous run.
    """

    def __init__(self):
        self._dpg2inode: dict[int, INode] = {}
        self._node_id2inode: dict[int, INode] = {}

    def add_node(
            self,
            inode: INode,
    ):
        self._node_id2inode[inode.node_id] = inode
        self._dpg2inode[inode.dpg_id] = inode

    def add_n_show(
            self,
            node: INode,
            parent: int | str,
            dpcm: int,
            pos: list[int] | None = None,
        ) -> str | int:
        node.submit(parent)

        self.add_node(node)
        # self.nodes[node.dpg_id] = node
        node.show(dpcm, pos)
        return node.dpg_id

    def rem_dpg(self, dpg_id: int):
        ret = self._dpg2inode[dpg_id]
        node_id = ret.node_id

        del self._dpg2inode[dpg_id]
        del self._node_id2inode[node_id]

    def rem_node_id(self, node_id: int):
        ret = self._node_id2inode[node_id]
        dpg_id = ret.dpg_id

        del self._dpg2inode[dpg_id]
        del self._node_id2inode[node_id]

    def get_dpg(self, dpg_id: int):
        return self._dpg2inode[dpg_id]

    def get_node_id(self, node_id: int):
        return self._node_id2inode[node_id]

    def values(self):
        for value in self._node_id2inode.values():
            yield value

    def items(self):
        for node_id in self._node_id2inode:
            inode = self._node_id2inode[node_id]
            yield (inode.node_id, inode.dpg_id), inode

    def dpg_ids(self):
        return list(self._dpg2inode.keys())

    def cpy_node_id_dict(self):
        return self._node_id2inode.copy()

    def get_free_node_id(self):
        """
        Returns a currently unused node_id
        """
        node_ids = self._node_id2inode.keys()
        node_id = 0
        while True:
            if node_id not in node_ids:
                return node_id
            else:
                node_id += 1

    def is_node_id_free(self, node_id: int) -> bool:
        """
        Returns true if the requested node_id is currently free and can be used
        """
        return node_id not in self._node_id2inode.keys()