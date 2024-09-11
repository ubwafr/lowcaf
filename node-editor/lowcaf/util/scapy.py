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

def get_field(pkt: Packet, layer_name: str, field: str):
    ssp = pkt.scapy_pkt
    ssp = ssp.getlayer(layer_name)

    try:
        return ssp.getfieldval(field)
    except AttributeError as e:
        ssp.show()
        raise AttributeError(f'{field} not present. See add output') \
            from e
