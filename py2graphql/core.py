import json
import math
import numbers

import requests


class InfinityNotSupportedError(Exception):
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


class Query(object):
    """
    Construct a GraphQL query
    """

    def __init__(
        self,
        operation_type="query",
        client=None,
        parent=None,
        operation_name=None,
        operation_variables=[],
    ):
        """
        Kwargs:
           name (str): Client used for sending queries.
           client: Client used for sending queries.
           parent (Query): Query that calls this query.
       """

        self._operation_type = operation_type
        self._nodes = []
        self._call_args = None
        self._values_to_show = []
        self._client = client
        self._parent = parent
        self._operation_name = operation_name
        self._operation_variables = operation_variables

    def __getattr__(self, key):
        q = Query(operation_type=key, parent=self)
        self._nodes.append(q)
        return q

    def __call__(self, *args, **kwargs):
        self._call_args = kwargs
        return self

    def values(self, *args):
        self._values_to_show.extend(args)
        return self

    def to_graphql(self, indentation=2):
        return self._get_root()._to_graphql(indentation=indentation)

    def _to_graphql(self, tab=2, indentation=2):
        if not indentation:
            tab = 0
            nl = ""
        else:
            nl = "\n"

        def serialize_arg(arg):
            if isinstance(arg, bool):
                return "true" if arg else "false"
            if isinstance(arg, type(None)):
                return "null"
            elif isinstance(arg, numbers.Number):
                if math.isinf(arg):
                    raise InfinityNotSupportedError(
                        "Graphql doesn't support infinite floats"
                    )
                return str(arg)
            elif isinstance(arg, Literal):
                return arg.name
            elif isinstance(arg, Variable):
                return "${}".format(arg.name)
            elif isinstance(arg, list):
                return "[{}]".format(", ".join(map(serialize_arg, arg)))
            elif isinstance(arg, dict):
                return "{{{}}}".format(
                    ", ".join(
                        ["{}: {}".format(k, serialize_arg(v)) for k, v in arg.items()]
                    )
                )
            elif isinstance(arg, str):
                arg = (
                    arg.replace("\\", "\\\\")
                    .replace("\f", "\\f")
                    .replace("\n", "\\n")
                    .replace("\r", "\\r")
                    .replace("\v", "")
                    .replace('"', '\\"')
                )
                return f'"{arg}"'
            else:
                raise Exception(arg)

        if self._call_args:
            args = ", ".join(
                [
                    "{0}: {1}".format(k, serialize_arg(v))
                    for k, v in self._call_args.items()
                ]
            )
            name = "{0}({1})".format(self._operation_type, args)
        else:
            name = self._operation_type

        nodes = [v for v in self._values_to_show]
        nodes.extend(
            [
                node._to_graphql(tab=tab + indentation, indentation=indentation)
                for node in self._nodes
            ]
        )

        def serialize_node(node):
            if isinstance(node, str):
                return node
            elif isinstance(node, Aliased):
                return "{}: {}".format(node.alias, node.name)
            else:
                raise Exception()

        if nodes:
            nodes = map(serialize_node, nodes)
            if indentation:
                nodes_str = ("\n" + " " * tab).join(nodes)
            else:
                nodes_str = " ".join(nodes)

            # Determine the operation
            if self._operation_name:
                operation = " {name}({variables})".format(
                    name=self._operation_name or "",
                    variables=",".join(
                        "{}: {}".format(k, v) for k, v in self._operation_variables
                    ),
                )
            else:
                operation = ""

            return "{op_type} {operation}{{{nl}{opening_tab}{nodes}{nl}{closing_tab}}}".format(
                op_type=name,
                operation=operation,
                opening_tab=" " * tab,
                closing_tab=" " * (tab - indentation),
                nodes=nodes_str,
                nl=nl,
            )
        else:
            return "{name} {{{nl}}}".format(name=name, nl=nl)

    def _get_root(self):
        if self._parent:
            return self._parent._get_root()
        else:
            return self

    def __getitem__(self, x):
        return self.fetch()[x]

    def fetch(self, variables={}):
        root = self._get_root()
        client = root._client
        graphql = root.to_graphql()

        response_content = client.fetch(graphql, variables)

        errors = response_content.get("errors")
        if errors is not None:
            raise GraphQLError(response_content)

        data = response_content.get("data", {})

        return client.pre_response(data, root_node=root)

    async def fetch_async(self, variables={}):
        root = self._get_root()
        client = root._client
        graphql = root.to_graphql()

        response_content = await client.fetch_async(graphql, variables)

        errors = response_content.get("errors")
        if errors is not None:
            raise GraphQLError(response_content)

        data = response_content.get("data", {})

        return client.pre_response(data, root_node=root)

    def __str__(self):
        return self.to_graphql()

    def __iter__(self):
        item = self.fetch()
        if isinstance(item, dict):
            return item.items()
        elif isinstance(item, list):
            return iter(item)
        else:
            raise Exception


class Mutation(Query):
    def __init__(self, operation_type="mutation", **kwargs):
        super(Mutation, self).__init__(operation_type=operation_type, **kwargs)


class Client(object):
    def __init__(self, url, headers, middleware=[]):
        self.url = url
        self.headers = headers
        self.middleware = [mw() for mw in middleware]

    def query(self, **kwargs):
        return Query(client=self, **kwargs)

    def mutation(self, **kwargs):
        return Mutation(client=self, **kwargs)

    def pre_response(self, result_dict, root_node):
        for mw in self.middleware:
            result_dict = mw.pre_response(result_dict, root_node)
        return result_dict

    def do_request(self, body):
        return requests.post(self.url, body, headers=self.headers)

    async def do_request_async(self, body):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.url, data=body, headers=self.headers
            ) as response:
                await response.text()
                return response

    def fetch(self, graphql, variables={}):
        body = {"query": graphql}

        if variables:
            body["variables"] = variables

        r = self.do_request(json.dumps(body))

        if r.status_code != 200:
            raise GraphQLEndpointError(
                r.content, status_code=r.status_code, response_object=r
            )

        return json.loads(r.content)

    async def fetch_async(self, graphql, variables={}):
        body = {"query": graphql}

        if variables:
            body["variables"] = variables

        r = await self.do_request_async(json.dumps(body))

        status_code = r.status
        content = await r.text()

        if status_code != 200:
            raise GraphQLEndpointError(
                content, status_code=status_code, response_object=r
            )
        return json.loads(content)
