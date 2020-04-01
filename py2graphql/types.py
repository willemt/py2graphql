class Aliased(object):
    def __init__(self, name, alias):
        self.alias = alias
        self.name = name


class Variable(object):
    def __init__(self, name):
        self.name = name


class Literal(object):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return self.name
