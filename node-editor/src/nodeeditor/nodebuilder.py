from src.nodes.ifaces.inode import INode
from src.nodes.ifaces.rnode import RNode


class NodeBuilder:
    i2r: list[tuple[type[INode], type[RNode]]] = []

    @classmethod
    def register_node(cls, inode: type[INode], rnode: type[RNode]):
        assert isinstance(inode, type(INode))
        assert isinstance(rnode, type(RNode))

        cls.i2r.append((inode, rnode))

    @classmethod
    def convert_i2r(cls, inode: INode) -> RNode:
        for i, r in cls.i2r:
            print(r)
            if isinstance(inode, i):
                return r.create_from_inode(inode)

    @classmethod
    def get_inode_cls(cls) -> list[type[INode]]:
        return [i for (i, r) in cls.i2r]

    @classmethod
    def get_name_inode_dict(cls) -> dict[str, type[INode]]:
        return {i.disp_name(): i for (i, r) in cls.i2r}

    @classmethod
    def get_rnode_cls(cls) -> list[type[RNode]]:
        return [r for (i, r) in cls.i2r]

    @classmethod
    def convert_i2r_dict(
            cls,
            d: dict[int, INode]
    ) -> dict[int, RNode]:
        return {k: cls.convert_i2r(i) for k, i in d.items()}
