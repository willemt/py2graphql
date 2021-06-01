class InfinityNotSupportedError(Exception):
    pass


class ValuesRequiresArgumentsError(Exception):
    pass


class GraphQLError(Exception):
    """GraphQL endpoint responded with a GraphQL error"""

    def __init__(self, response):
        self.response = response
        super().__init__(response)


class GraphQLEndpointError(Exception):
    """GraphQL endpoint didn't respond with a JSON object"""

    def __init__(self, response, status_code, response_object):
        self.response = response
        self.status_code = status_code
        self.response_object = response_object
        super().__init__(response)


class UnserializableTypeError(Exception):
    pass
