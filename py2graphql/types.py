class Aliased(object):
    def __init__(self, name: str, alias: str):
        self.alias = alias
        self.name = name


class Variable(object):
    def __init__(self, name: str):
        self.name = name


class Literal(object):
    def __init__(self, name: str):
        self.name = name

    def __repr__(self):
        return self.name
