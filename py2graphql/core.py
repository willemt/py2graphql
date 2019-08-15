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


class Query(object):
    """
    Construct a GraphQL query
    """
    def __init__(self, name='query', client=None, parent=None):
        self._name = name
        self._nodes = []
        self._call_args = None
        self._values_to_show = []
        self._client = client
        self._parent = parent

    def __getattr__(self, key):
        q = Query(name=key, parent=self)
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
            nl = ''
        else:
            nl = '\n'

        def serialize_arg(arg):
            if isinstance(arg, bool):
                return 'true' if arg else 'false'
            elif isinstance(arg, numbers.Number):
                return str(arg)
            else:
                return '"{0}"'.format(arg)

        if self._call_args:
            args = ', '.join([
                '{0}: {1}'.format(k, serialize_arg(v))
                for k, v in self._call_args.items()
            ])
            name = '{0}({1})'.format(self._name, args)
        else:
            name = self._name

        nodes = [v for v in self._values_to_show]
        nodes.extend([
            node._to_graphql(tab=tab + indentation, indentation=indentation)
            for node in self._nodes
        ])

        if nodes:
            if indentation:
                nodes_str = ('\n' + ' '*tab).join([v for v in nodes])
            else:
                nodes_str = ' '.join([v for v in nodes])
            return '{name} {{{nl}{opening_tab}{nodes}{nl}{closing_tab}}}'.format(
                name=name,
                opening_tab=' '*tab,
                closing_tab=' '*(tab - indentation),
                nodes=nodes_str,
                nl=nl,
            )
        else:
            return '{name} {{{nl}}}'.format(
                name=name,
                opening_tab=' '*tab,
                closing_tab=' '*(tab - indentation),
                nl=nl,
            )

    def _get_root(self):
        if self._parent:
            return self._parent._get_root()
        else:
            return self

    def __getitem__(self, x):
        return getattr(self.fetch(), x)

    def fetch(self):
        root = self._get_root()
        client = root._client
        graphql = root.to_graphql()
        body = {
            'query': graphql
        }
        r = requests.post(client.url, json.dumps(body), headers=client.headers)

        if r.status_code != 200:
            try:
                raise GraphQLError(json.loads(r.content))
            except json.JSONDecodeError:
                raise GraphQLEndpointError(r.content)

        response_content = json.loads(r.content)
        data = response_content['data']
        errors = response_content.get('errors')

        result_dict = addict.Dict(data)
        if errors is not None:
            result_dict.update(_errors=errors)

        return result_dict


class Mutation(Query):
    def __init__(self, name='mutation', **kwargs):
        super(Mutation, self).__init__(name=name, **kwargs)


class Client(object):
    def __init__(self, url, headers):
        self.url = url
        self.headers = headers

    def query(self):
        return Query(client=self)
