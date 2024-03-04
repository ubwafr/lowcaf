from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional

from scapy.packet import Packet
from scapy.all import *

BYTE_ORDER: Literal['big', 'little'] = 'big'


class MsgIncompleteError(RuntimeError):
    pass


class BBPacket:
    """
    This is how packets are internally represented within BB and thus how the
    nodes will interact with packets.
    """

    def __init__(self,
                 data: Packet,
                 timestamp: int,
                 dropped: bool = False,
                 metadata: Optional[dict] = None):
        self.scapy_pkt: Packet = data
        self.timestamp: int = timestamp
        self.dropped: bool = dropped
        self.metadata: dict = metadata if metadata is not None else {}


class DecoderSim2BB:
    """
    This class provides an overall handler for all messages received from the
    simulation application
    """

    CMD_PKT: int = 0x01  # BBPacket Message
    CMD_EOD: int = 0x02  # End-of-Data Message

    @classmethod
    def buff2msgs(cls, buff: bytes) -> tuple[list, bytes]:
        """
        Extract RcvMessages from a buffer

        Args:
            buff: The buffer containing RcvMessages in serialized form

        Returns:
            msgs, rem: A list of RcvMessages and remaining bytes that were
            not part of the last RcvMessage, but belong to the next one which
            was only partially present in the buffer
        """
        out = []
        ptr = 0
        while ptr < len(buff):
            cmd: int = int.from_bytes(
                buff[ptr:ptr + 1], BYTE_ORDER, signed=False)

            try:
                match cmd:
                    case cls.CMD_EOD:
                        msg, ptr = EODMsg.buff2msg(buff, ptr)
                        out.append(msg)
                    case cls.CMD_PKT:
                        msg, ptr = MsgSim2BB.buff2msg(buff, ptr)
                        out.append(msg)
                    case _:
                        raise NotImplementedError(
                            f'Command {cmd} is unknown'
                        )
            except MsgIncompleteError:
                return out, buff[ptr:]

        return out, bytes()


class DecoderBB2Sim:
    """
    This class provides an overall handler for all messages received from the
    simulation application
    """

    CMD_PKT: int = 0x01  # BBPacket Message
    CMD_EOD: int = 0x02  # End-of-Data Message

    @classmethod
    def buff2msgs(cls, buff: bytes) -> tuple[list, bytes]:
        """
        Extract RcvMessages from a buffer

        Args:
            buff: The buffer containing RcvMessages in serialized form

        Returns:
            msgs, rem: A list of RcvMessages and remaining bytes that were
            not part of the last RcvMessage, but belong to the next one which
            was only partially present in the buffer
        """
        out = []
        ptr = 0
        while ptr < len(buff):
            cmd: int = int.from_bytes(
                buff[ptr:ptr + 1], BYTE_ORDER, signed=False)

            try:
                match cmd:
                    case cls.CMD_EOD:
                        msg, ptr = EODMsg.buff2msg(buff, ptr)
                        out.append(msg)
                    case cls.CMD_PKT:
                        msg, ptr = MsgBB2Sim.buff2msg(buff, ptr)
                        out.append(msg)
                    case _:
                        raise NotImplementedError(
                            f'Command {cmd} is unknown'
                        )
            except MsgIncompleteError:
                return out, buff[ptr:]

        return out, bytes()


class Msg(ABC):

    @abstractmethod
    def serialize(self) -> bytes:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def buff2msg(cls,
                 buff: bytes,
                 ptr: int) -> tuple['Msg', int]:
        raise NotImplementedError


class EODMsg(Msg):
    def serialize(self) -> bytes:
        return DecoderSim2BB.CMD_EOD.to_bytes(1, BYTE_ORDER, signed=False)

    @classmethod
    def buff2msg(cls, buff: bytes, ptr: int) -> tuple['Msg', int]:
        return EODMsg(), ptr + 1


class MsgSim2BB(Msg):
    """
    This defines the message format which we receive from NS3 instances. Before
    the contents are forwarded into BBs packet processing the message should be
    transformed into a BBPacket.
    """

    def __init__(self,
                 ns3_node_id: int,
                 node_id: int,
                 delay_ns: int,
                 data: bytes):
        self.node_id: int = node_id
        self.ns3_node_id: int = ns3_node_id
        self.delay_ns: int = delay_ns
        self.data: bytes = data

    def __eq__(self, other):
        if isinstance(other, MsgSim2BB):
            return self.__dict__ == other.__dict__
        else:
            return NotImplemented

    def serialize(self) -> bytes:
        buf = bytes()
        buf += b'\x01'
        buf += self.ns3_node_id.to_bytes(4, BYTE_ORDER, signed=False)
        buf += self.node_id.to_bytes(4, BYTE_ORDER, signed=False)
        buf += self.delay_ns.to_bytes(8, BYTE_ORDER, signed=False)
        buf += len(self.data).to_bytes(4, BYTE_ORDER, signed=False)
        buf += self.data

        return buf

    @classmethod
    def buff2msg(cls,
                 buff: bytes,
                 ptr: int) -> tuple['MsgSim2BB', int]:

        cmd: int = int.from_bytes(
            buff[ptr:ptr + 1], BYTE_ORDER, signed=False)
        ptr += 1

        ns3_node_id: int = int.from_bytes(
            buff[ptr:ptr + 4], BYTE_ORDER, signed=False)
        ptr += 4

        node_id: int = int.from_bytes(
            buff[ptr:ptr + 4], BYTE_ORDER, signed=False)
        ptr += 4

        delay_ns: int = int.from_bytes(
            buff[ptr: ptr + 8], BYTE_ORDER, signed=False)
        ptr += 8

        print(delay_ns)

        length = int.from_bytes(
            buff[ptr:ptr + 4], BYTE_ORDER, signed=False)
        ptr += 4

        print(length)

        data: bytes = buff[ptr: ptr + length]
        ptr += length

        if ptr > len(buff):
            # this message was not fully contained
            raise MsgIncompleteError

        return MsgSim2BB(ns3_node_id, node_id, delay_ns, data), ptr

    def __str__(self):
        return ('PKTMsg Content:\n'
                f'\tNode ID: {self.node_id}\n'
                f'\tNS3 Node ID: {self.ns3_node_id}\n'
                f'\tDelay: {self.delay_ns}\n'
                f'\tData: {self.data}\n'
                f'\tLength: {len(self.data)}\n')


class MsgBB2Sim(Msg):
    """
    The message format when sending scapy_pkt back to an NS3 instance.
    """

    def __init__(self,
                 delay_ns: int,
                 data: bytes,
                 mac: bytes,
                 proto: bytes):
        self.delay_ns: int = delay_ns
        self.data: bytes = data
        self.mac: bytes = mac
        self.proto: bytes = proto

    def serialize(self) -> bytes:
        buf = bytes()
        buf += b'\x01'
        buf += self.delay_ns.to_bytes(8, BYTE_ORDER, signed=False)
        # buf += self.mac
        buf += self.proto
        buf += len(self.data).to_bytes(4, BYTE_ORDER, signed=False)
        buf += self.data

        return buf

    @classmethod
    def buff2msg(cls, buff: bytes, ptr: int) -> tuple['Msg', int]:
        cmd: int = int.from_bytes(
            buff[ptr:ptr + 1], BYTE_ORDER, signed=False)
        ptr += 1

        delay_ns: int = int.from_bytes(
            buff[ptr:ptr + 8], BYTE_ORDER, signed=False)
        ptr += 8

        mac: bytes = buff[ptr:ptr + 17]
        ptr += 17

        proto: bytes = buff[ptr: ptr + 2]
        ptr += 2

        length = int.from_bytes(
            buff[ptr:ptr + 4], BYTE_ORDER, signed=False)
        ptr += 4

        data: bytes = buff[ptr: ptr + length]
        ptr += length

        if ptr > len(buff):
            # this message was not fully contained
            raise MsgIncompleteError

        return MsgBB2Sim(delay_ns, data, mac, proto), ptr

    def __str__(self):
        data = self.serialize()

        return ('TxMessage Content:\n'
                f'\tCommand: {data[0:1]}\n'
                f'\tDelay [ns]: {data[1:9]}\n'
                f'\tMAC address: {data[9:26]}\n'
                f'\tProto: {data[26:28]} {int.from_bytes(data[26:28], "little")}\n'
                f'\tLength: {data[28:32]} {int.from_bytes(data[28:32], "little")}\n'
                f'\tPayload: {data[32:32 + len(self.data)]}\n')
