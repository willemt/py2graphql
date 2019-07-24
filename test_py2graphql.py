import json
import unittest

import mock

from py2graphql import (
    Client,
    GraphQLEndpointError,
    GraphQLError,
    Query,
)


class Py2GraphqlTests(unittest.TestCase):
    def test_function(self):
        self.assertEqual(
            Query().repository(owner='juliuscaeser', name='rome').values('title', 'url').to_graphql(),
            'query {\n  repository(owner: "juliuscaeser", name: "rome") {\n    title\n    url\n  }\n}',
        )

    def test_boolean(self):
        self.assertEqual(
            Query().repository(owner='juliuscaeser', test=True).values('title', 'url').to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: true) {title url}}',
        )

    def test_number(self):
        self.assertEqual(
            Query().repository(owner='juliuscaeser', test=10).values('title', 'url').to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: 10) {title url}}',
        )

    def test_float(self):
        self.assertEqual(
            Query().repository(owner='juliuscaeser', test=10.0).values('title', 'url').to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: 10.0) {title url}}',
        )

    def test_mutation_boolean(self):
        self.assertEqual(
            Query(name='mutation').repository(owner='juliuscaeser', isAdmin=True).values('title', 'url').to_graphql(indentation=0),
            'mutation {repository(owner: "juliuscaeser", isAdmin: true) {title url}}',
        )

    def test_subscripting_query_fetches(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers):
            r = FakeResponse()
            r.status_code = 200
            r.content = json.dumps({'data': {'repository': {'title': "xxx", 'url': 'example.com'}}})
            return r

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch('requests.post', http_mock):
            self.assertEqual(
                Query(client=Client('http://example.com', {})).repository(owner='juliuscaeser', test=10).values('title', 'url')['repository'],
                {'title': 'xxx', 'url': 'example.com'},
            )

    def test_raise_exceptions(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers):
            r = FakeResponse()
            r.status_code = 400
            r.content = json.dumps({'errors': {'repository': 'xxx'}})
            return r

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch('requests.post', http_mock):
            try:
                Query(client=Client('http://example.com', {})).repository(owner='juliuscaeser', test=10).values('title', 'url')['repository']
            except GraphQLError as e:
                self.assertEqual(e.response, {'errors': {'repository': 'xxx'}})
            else:
                assert False

    def test_raise_endpoint_exceptions(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers):
            r = FakeResponse()
            r.status_code = 400
            r.content = 'blahblah'
            return r

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch('requests.post', http_mock):
            try:
                Query(client=Client('http://example.com', {})).repository(owner='juliuscaeser', test=10).values('title', 'url')['repository']
            except GraphQLEndpointError as e:
                self.assertEqual(e.response, 'blahblah')
            else:
                assert False


if __name__ == '__main__':
    unittest.main()