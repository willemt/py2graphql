import json
from typing import List

import aiohttp

import requests

from tenacity import retry, stop_after_attempt  # type: ignore
from tenacity.wait import wait_fixed  # type: ignore

from .exception import GraphQLEndpointError, GraphQLError, ValuesRequiresArgumentsError
from .serialization import serialize_arg
from .types import Aliased


class Query(object):
    """
    Construct a GraphQL query
    """

    def __init__(
        self,
        operation_type: str = "query",
        client=None,
        parent=None,
        operation_name: str = None,
        operation_variables=[],
    ):
        """
        Kwargs:
           name (str): Client used for sending queries.
           client: Client used for sending queries.
           parent (Query): Query that calls this query.
       """

        self._operation_type = operation_type
        self._nodes: List[Query] = []
        self._call_args = None
        self._values_to_show: List[str] = []
        self._client = client
        self._parent = parent
        self._operation_name = operation_name
        self._operation_variables = operation_variables

    def __getattr__(self, key: str):
        q = Query(operation_type=key, parent=self)
        self._nodes.append(q)
        return q

    def __call__(self, *args, **kwargs):
        self._call_args = kwargs
        return self

    def values(self, *args):
        if not args:
            raise ValuesRequiresArgumentsError
        self._values_to_show.extend(args)
        return self

    def to_graphql(self, indentation: int = 2):
        return self._get_root()._to_graphql(indentation=indentation)

    def _to_graphql(self, tab: int = 2, indentation: int = 2):
        if not indentation:
            tab = 0
            nl = ""
        else:
            nl = "\n"

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
            elif isinstance(node, Query):
                return node._to_graphql()
            else:
                raise Exception()

        if nodes:
            nodes = list(map(serialize_node, nodes))
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

    def __getitem__(self, x: str):
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


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
async def do_request_async(url: str, body, headers: dict):
    timeout = aiohttp.ClientTimeout(total=25)
    async with aiohttp.ClientSession() as session:
        async with session.post(
            url, data=body, headers=headers, timeout=timeout
        ) as response:
            await response.text()
            return response


class Client(object):
    def __init__(self, url: str, headers, middleware=[]):
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
        return requests.post(self.url, body, headers=self.headers, timeout=25)

    async def do_request_async(self, body):
        return await do_request_async(self.url, body, self.headers)

    def fetch(self, graphql: str, variables={}):
        body = {"query": graphql}

        if variables:
            body["variables"] = variables

        r = self.do_request(json.dumps(body))

        if r.status_code != 200:
            raise GraphQLEndpointError(
                r.content, status_code=r.status_code, response_object=r
            )

        return json.loads(r.content)

    async def fetch_async(self, graphql: str, variables={}):
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
