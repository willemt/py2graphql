import asyncio
import enum
import json
import unittest
from string import printable
from unittest import mock
from unittest.mock import patch

from graphql import parse
from hypothesis import given
from hypothesis import strategies as st

from py2graphql import Aliased
from py2graphql import Client
from py2graphql import GraphQLEndpointError
from py2graphql import GraphQLError
from py2graphql import InfinityNotSupportedError
from py2graphql import Literal
from py2graphql import Query
from py2graphql import UnserializableTypeError
from py2graphql import ValuesRequiresArgumentsError
from py2graphql.middleware import AddictMiddleware
from py2graphql.middleware import AutoSubscriptingMiddleware


# Helper function to create a coroutine mock
def create_async_mock(return_value=None):
    """Create a mock that returns a coroutine function which returns the given value."""
    async def mock_coroutine(*args, **kwargs):
        return return_value
    return mock.Mock(side_effect=mock_coroutine)


class MyEnum(enum.Enum):
    ABC = "abc"
    DEF = "def"


class Py2GraphqlTests(unittest.TestCase):
    def test_simple(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", name="rome")
            .values("title", "url")
            .to_graphql(),
            'query {\n  repository(owner: "juliuscaeser", name: "rome") {\n    title\n    url\n  }\n}',
        )

    def test_boolean(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test=True)
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: true) {title url}}',
        )

    def test_none(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test=None)
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: null) {title url}}',
        )

    def test_literal(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", orderBy=Literal("age_ASC"))
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", orderBy: age_ASC) {title url}}',
        )

    def test_number(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test=10)
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: 10) {title url}}',
        )

    def test_float(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test=10.0)
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: 10.0) {title url}}',
        )

    def test_list(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test=[])
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: []) {title url}}',
        )

    def test_dict(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test={"a": 1})
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: {a: 1}) {title url}}',
        )

    def test_enum(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test=MyEnum.ABC)
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: ABC) {title url}}',
        )

    def test_function(self):
        try:
            Query().repository(owner="juliuscaeser", test=lambda: "").values(
                "title", "url"
            ).to_graphql(indentation=0)
        except UnserializableTypeError:
            pass
        else:
            raise Exception

    def test_list_with_contents(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test=[1])
            .values("title", "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: [1]) {title url}}',
        )

    def test_nested(self):
        x = (
            Query()
            .repository(owner="juliuscaeser", test=[1])
            .values("title", "url", Query().commits.values("id"))
            .to_graphql(indentation=0)
        )
        self.assertEqual(
            x,
            'query {repository(owner: "juliuscaeser", test: [1]) {title url commits {\n'
            "  id\n"
            "}}}",
        )
        parse(x)

    def test_nested_nested(self):
        x = (
            Query()
            .repository(owner="juliuscaeser", test=[1])
            .values(
                "title",
                "url",
                Query().commits.values("id", Query().authors.values("name", "id")),
            )
            .to_graphql(indentation=0)
        )
        self.assertEqual(
            x,
            'query {repository(owner: "juliuscaeser", test: [1]) {title url commits {\n'
            "  id\n"
            "  authors {\n"
            "  name\n"
            "  id\n"
            "}\n"
            "}}}",
        )
        parse(x)

    def test_mutation_boolean(self):
        self.assertEqual(
            Query(operation_type="mutation")
            .repository(owner="juliuscaeser", isAdmin=True)
            .values("title", "url")
            .to_graphql(indentation=0),
            'mutation {repository(owner: "juliuscaeser", isAdmin: true) {title url}}',
        )

    def test_alias(self):
        self.assertEqual(
            Query()
            .repository(owner="juliuscaeser", test=True)
            .values(Aliased("title", "xxx"), "url")
            .to_graphql(indentation=0),
            'query {repository(owner: "juliuscaeser", test: true) {xxx: title url}}',
        )

    def test_empty_values(self):
        try:
            self.assertEqual(
                Query()
                .repository(owner="juliuscaeser", isAdmin=True)
                .values()
                .to_graphql(indentation=0),
                'query {repository(owner: "juliuscaeser", isAdmin: true) {title url}}',
            )
        except ValuesRequiresArgumentsError:
            pass
        else:
            assert False

    def test_subscripting_query_fetches(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers, **kwargs):
            r = FakeResponse()
            r.status_code = 200
            r.content = json.dumps(
                {"data": {"repository": {"title": "xxx", "url": "example.com"}}}
            )
            return r

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch("requests.post", http_mock):
            self.assertEqual(
                Query(
                    client=Client(
                        "http://example.com", {}, middleware=[AddictMiddleware]
                    )
                )
                .repository(owner="juliuscaeser", test=10)
                .values("title", "url")["repository"],
                {"title": "xxx", "url": "example.com"},
            )

    def test_fetch_async(self):
        async def task():
            with patch("aiohttp.ClientSession.post") as mocked:
                mocked.return_value.__aenter__.return_value.status = 200
                mocked.return_value.__aenter__.return_value.text = create_async_mock(
                    json.dumps(
                        {"data": {"repository": {"title": "xxx", "url": "example.com"}}}
                    )
                )
                result = (
                    await Query(client=Client("http://example.com", {}))
                    .repository(owner="juliuscaeser", test=10)
                    .values("title", "url")
                    .fetch_async()
                )
                self.assertEqual(
                    result, {"repository": {"title": "xxx", "url": "example.com"}}
                )

        loop = asyncio.new_event_loop()
        loop.run_until_complete(task())
        loop.close()

    def test_fetch_async_retry(self):
        async def task():
            class ReturnValue:
                pass

            with patch("aiohttp.ClientSession.post") as mocked:
                ret = ReturnValue
                ret.status = 200
                ret.text = create_async_mock(
                    json.dumps(
                        {"data": {"repository": {"title": "xxx", "url": "example.com"}}}
                    )
                )
                mocked.return_value.__aenter__.side_effect = [Exception(), ret]

                result = (
                    await Query(client=Client("http://example.com", {}))
                    .repository(owner="juliuscaeser", test=10)
                    .values("title", "url")
                    .fetch_async()
                )
                self.assertEqual(
                    result, {"repository": {"title": "xxx", "url": "example.com"}}
                )

        loop = asyncio.new_event_loop()
        loop.run_until_complete(task())
        loop.close()

    def test_auto_subscript(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers, **kwargs):
            r = FakeResponse()
            r.status_code = 200
            r.content = json.dumps(
                {"data": {"repository": {"title": "xxx", "url": "example.com"}}}
            )
            return r

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch("requests.post", http_mock):
            self.assertEqual(
                Query(
                    client=Client(
                        "http://example.com",
                        {},
                        middleware=[AutoSubscriptingMiddleware],
                    )
                )
                .repository(owner="juliuscaeser", test=10)
                .values("title", "url")
                .fetch(),
                {"title": "xxx", "url": "example.com"},
            )

    def test_auto_subscript_iteration(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers, **kwargs):
            r = FakeResponse()
            r.status_code = 200
            r.content = json.dumps(
                {"data": {"repos": [{"title": "xxx", "url": "example.com"}]}}
            )
            return r

        client = Client(
            "http://example.com", {}, middleware=[AutoSubscriptingMiddleware]
        )

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch("requests.post", http_mock):
            for x in (
                Query(client=client)
                .repos(owner="juliuscaeser", test=10)
                .values("title", "url")
            ):
                self.assertEqual(x["title"], "xxx")

    def test_iteration(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers, **kwargs):
            r = FakeResponse()
            r.status_code = 200
            r.content = json.dumps(
                {"data": {"repos": [{"title": "xxx", "url": "example.com"}]}}
            )
            return r

        client = Client("http://example.com", {})

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch("requests.post", http_mock):
            for x in (
                Query(client=client)
                .repos(owner="juliuscaeser", test=10)
                .values("title", "url")["repos"]
            ):
                self.assertEqual(x["title"], "xxx")

    def test_syntax_error_response(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers, **kwargs):
            r = FakeResponse()
            r.status_code = 200
            r.content = json.dumps(
                {
                    "errors": [
                        {
                            "message": 'Syntax Error GraphQL (2:18) Unexpected Name "null"\n',
                            "locations": [{"line": 2, "column": 18}],
                        }
                    ]
                }
            )
            return r

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch("requests.post", http_mock):
            try:
                Query(client=Client("http://example.com", {})).repository(
                    owner=None, test=10
                ).values("title", "url").fetch()
            except GraphQLError as e:
                self.assertEqual(
                    e.response,
                    {
                        "errors": [
                            {
                                "locations": [{"column": 18, "line": 2}],
                                "message": 'Syntax Error GraphQL (2:18) Unexpected Name "null"\n',
                            }
                        ]
                    },
                )
            else:
                assert False

    def test_raise_exceptions(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers, **kwargs):
            r = FakeResponse()
            r.status_code = 400
            r.content = json.dumps({"errors": {"repository": "xxx"}})
            return r

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch("requests.post", http_mock):
            try:
                Query(client=Client("http://example.com", {})).repository(
                    owner="juliuscaeser", test=10
                ).values("title", "url")["repository"]
            except GraphQLEndpointError as e:
                self.assertEqual(e.response, '{"errors": {"repository": "xxx"}}')
            else:
                assert False

    def test_raise_endpoint_exceptions(self):
        class FakeResponse:
            pass

        def fake_request(url, body, headers, **kwargs):
            r = FakeResponse()
            r.status_code = 400
            r.content = "blahblah"
            return r

        http_mock = mock.Mock(side_effect=fake_request)
        with mock.patch("requests.post", http_mock):
            try:
                Query(client=Client("http://example.com", {})).repository(
                    owner="juliuscaeser", test=10
                ).values("title", "url")["repository"]
            except GraphQLEndpointError as e:
                self.assertEqual(e.response, "blahblah")
                self.assertEqual(e.status_code, 400)
            else:
                assert False

    @given(st.fixed_dictionaries({"xxx": st.text(printable)}))
    def test_fuzz(self, data):
        query = (
            Query(client=Client("http://example.com", {}))
            .repository(**data)
            .values("id")
        )
        parse(str(query))

    @given(st.fixed_dictionaries({"xxx": st.floats(allow_infinity=True)}))
    def test_fuzz_floats(self, data):
        query = (
            Query(client=Client("http://example.com", {}))
            .repository(**data)
            .values("id")
        )
        try:
            parse(str(query))
        except InfinityNotSupportedError:
            pass

    @given(st.fixed_dictionaries({"xxx": st.integers()}))
    def test_fuzz_integers(self, data):
        query = (
            Query(client=Client("http://example.com", {}))
            .repository(**data)
            .values("id")
        )
        parse(str(query))

    @given(st.fixed_dictionaries({"xxx": st.lists(st.text(printable))}))
    def test_fuzz_lists(self, data):
        query = (
            Query(client=Client("http://example.com", {}))
            .repository(**data)
            .values("id")
        )
        parse(str(query))


if __name__ == "__main__":
    unittest.main()
