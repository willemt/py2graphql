import json
import numbers

import addict

import requests


class GraphQLError(Exception):
    """GraphQL endpoint responded with a GraphQL error"""

    def __init__(self, response):
        self.response = response
        super().__init__(response)


class GraphQLEndpointError(Exception):
    """GraphQL endpoint didn't respond with a JSON object"""

    def __init__(self, response):
        self.response = response
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
            else:
                return f'"{arg}"'

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
        return getattr(self.fetch(), x)

    def fetch(self, variables={}):
        root = self._get_root()
        client = root._client
        graphql = root.to_graphql()

        body = {"query": graphql}

        if variables:
            body["variables"] = variables

        r = requests.post(client.url, json.dumps(body), headers=client.headers)

        if r.status_code != 200:
            try:
                raise GraphQLError(json.loads(r.content))
            except json.JSONDecodeError:
                raise GraphQLEndpointError(r.content)

        response_content = json.loads(r.content)

        errors = response_content.get("errors")
        if errors is not None:
            raise GraphQLError(json.loads(r.content))

        data = response_content.get("data", {})
        result_dict = addict.Dict(data)
        return result_dict

    def __str__(self):
        return self.to_graphql()

    def __iter__(self):
        return self.fetch().items()


class Mutation(Query):
    def __init__(self, operation_type="mutation", **kwargs):
        super(Mutation, self).__init__(operation_type=operation_type, **kwargs)


class Client(object):
    def __init__(self, url, headers):
        self.url = url
        self.headers = headers

    def query(self, **kwargs):
        return Query(client=self, **kwargs)

    def mutation(self, **kwargs):
        return Mutation(client=self, **kwargs)
