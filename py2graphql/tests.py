from .core import Query


def test_simple():
    assert Query().tests.to_graphql(indentation=0) == """query {tests {}}"""


def test_medium():
    query = (
        Query()
        .repository(owner="juliuscaeser", name="rome")
        .pullRequest(number=2)
        .values("title", "url")
        .commits(last=250)
        .edges.node.commit.values("id", "message", "messageBody")
    )
    assert (
        query.to_graphql()
        == """
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
    """.strip()
    )
