1. GraphQL
2. Django queryset love
3. __getattr__ abuse
4. ???
5. Profit!!!


What
----
py2graphql is a Python GraphQL client that makes GraphQL feel better to use. It almost feels like you're using Django's ORM.

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

Installation
------------
.. code-block:: bash
   :class: ignore

   pip install py2graphql


