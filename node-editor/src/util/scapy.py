from scapy.packet import NoPayload, Packet


def get_layer(pkt: Packet, layer_name: str) -> Packet:
    layer_list = []
    while not isinstance(pkt, NoPayload):
        if pkt.name == layer_name:
            print('found')
            return pkt

        layer_list.append(pkt.name)
        pkt = pkt.payload
    else:
        msg = f"'{layer_name}' not in {layer_list}"
        raise KeyError(msg)
