1. GraphQL
2. __getattr__ abuse
3. ???
4. Profit!!!

Example
-------

The following Python equates to the preceding GraphQL

.. code-block:: python
   :class: ignore

   query = Query().repository(owner='juliuscaeser', name='rome').pullRequest(number=2).values('title', 'url').commits(last=250).edges.node.commit.values('id', 'message', 'messageBody')

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

   headers = {
       'Authorization': 'token MY_TOKEN',
   }
   Client(url=THE_URL, headers=headers).query().repository(owner='juliuscaeser', name='rome').fetch()

Installation
------------
.. code-block:: bash
   :class: ignore

   pip install py2graphql


