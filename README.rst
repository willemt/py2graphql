Py2graphql
##########

|pypi|

1. GraphQL
2. Django queryset love
3. ``__getattr__`` abuse
4. ???
5. Profit!!!


What
----
py2graphql is a Python GraphQL client that makes GraphQL feel better to use. It almost feels like you're using Django's ORM.


Installation
------------
.. code-block:: bash
   :class: ignore

   pip install py2graphql


Example
-------

This Python equates to the following GraphQL.

.. code-block:: python
   :class: ignore

   from py2graphql import Query

   Query().repository(owner='juliuscaeser', name='rome').pullRequest(number=2).values('title', 'url').commits(last=250).edges.node.commit.values('id', 'message', 'messageBody')

.. code-block:: graphql
   :class: ignore

   query {
     repository(owner: "juliuscaeser", name: "rome") {
       pullRequest(number: 2) {
         title
         url
         commits(last: 250) {
           edges {
             node {
               commit {
                 id
                 message
                 messageBody
               }
             }
           }
         }
       }
     }
   }

You can even use the library to do the HTTP requests:

.. code-block:: python
   :class: ignore

   from py2graphql import Client

   headers = {
       'Authorization': 'token MY_TOKEN',
   }
   Client(url=THE_URL, headers=headers).query().repository(owner='juliuscaeser', name='rome').fetch()

It also supports Mutations:

.. code-block:: python
   :class: ignore

   from py2graphql import Client, Query

   headers = {
       'Authorization': 'token MY_TOKEN',
   }
   client = Client(url=THE_URL, headers=headers)
   mutation = Query(name='mutation', client=client)


And multiple queries in a single request:

.. code-block:: python
   :class: ignore

   from py2graphql import Client, Query

   headers = {
       'Authorization': 'token MY_TOKEN',
   }
   query = Client(url=THE_URL, headers=headers).query().repository(owner='juliuscaeser', name='rome')
   query.pullRequest(number=2).values('title', 'url')
   query.releases(first=10).edges.node.values('name')
   query.get_graphql()

.. code-block:: graphql
   :class: ignore

   query {
     repository(owner: "juliuscaeser", name: "rome") {
        pullRequest(number: 2) {
          title
          url
        }
        releases(first: 10) {
          edges {
            node {
              name
            }
          }
        }
      }
   }

As well as GraphQL errors:

.. code-block:: python
   :class: ignore

   from py2graphql import Client, Query

   headers = {
       'Authorization': 'token MY_TOKEN',
   }
   result = Client(url=THE_URL, headers=headers).query().repository(owner='juliuscaeser', name='rome').fetch()
   result._errors
   [{'message': "Field 'repository' is missing required arguments: name", 'locations': [{'line': 7, 'column': 3}]}]


.. |pypi| image:: https://img.shields.io/pypi/v/py2graphql.svg?style=flat
   :target: https://pypi.python.org/pypi/py2graphql
