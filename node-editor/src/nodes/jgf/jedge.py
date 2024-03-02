from dataclasses import dataclass

from src.nodes.jgf.jfgkeys import JEDGE_SOURCE, JEDGE_TARGET, JEDGE_RELATION


@dataclass
class JEdge:
    source: int
    target: int
    relation: str

    def to_jgf(self):
        """
        Convert this Edge into JGF

        Source and target are stored as strings to comply with the JGF
        specification, which states that the edges must directly refer to
        the node IDs which in turn must be strings as JSON uses strings as keys
        """
        return {
            JEDGE_SOURCE: str(self.source),
            JEDGE_TARGET: str(self.target),
            JEDGE_RELATION: self.relation
        }

    @classmethod
    def from_jgf(cls, jgf: dict) -> 'JEdge':

        return cls(
            int(jgf[JEDGE_SOURCE]),
            int(jgf[JEDGE_TARGET]),
            jgf[JEDGE_RELATION]
        )

