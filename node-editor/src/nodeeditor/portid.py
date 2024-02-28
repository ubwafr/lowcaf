class PortID:
    def __init__(self, obj_id: int, port: int):
        self.obj_id: int = obj_id
        self.port: int = port

    def __str__(self):
        return f'Node_ID.Port: {self.obj_id}.{self.port}'

    def __repr__(self):
        return f'{self.__class__.__name__}({self.obj_id},{self.port})'
