from dataclasses import dataclass

from src.nodes.jgf.jfgkeys import JNODE_LABEL, JNODE_METADATA, JNODE_ID, JNODE_TYPE, \
    JNODE_POSITION, JNODE_ADD_METADATA, JNODE_ATTR_TYPE, JNODE_ATTR_ID


@dataclass
class JNode:
    node_id: int
    label: str
    node_type: str
    position: list[int]
    add_metadata: dict

    def to_jgf(self):
        return {
            self.node_id: {
                JNODE_LABEL: self.label,
                JNODE_METADATA: {
                    JNODE_ID: self.node_id,
                    JNODE_TYPE: self.node_type,
                    JNODE_POSITION: self.position,
                    JNODE_ADD_METADATA: self.add_metadata
                }
            }
        }

    @classmethod
    def init_attr(cls,
                  node_id: int,
                  attr_id: int | str,
                  add_metadata: dict | None = None):
        if add_metadata is None:
            add_metadata = {}
        add_metadata |= {JNODE_ATTR_ID: attr_id}
        return cls(node_id, JNODE_ATTR_TYPE, JNODE_ATTR_TYPE, [], add_metadata)

    @classmethod
    def from_jgf(cls, jgf: dict) -> 'JNode':
        meta = jgf[JNODE_METADATA]

        return cls(
            meta[JNODE_ID],
            jgf[JNODE_LABEL],
            meta[JNODE_TYPE],
            meta[JNODE_POSITION],
            meta[JNODE_ADD_METADATA]
        )

    def __eq__(self, other):
        if not isinstance(other, JNode):
            return NotImplemented

        return (self.node_id == other.node_id and
                self.label == other.label and
                self.node_type == other.node_type and
                self.position == other.position and
                self.add_metadata == other.add_metadata
                )
