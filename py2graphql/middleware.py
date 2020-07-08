class Middleware:
    def pre_response(self, result_dict, root_node):
        return result_dict


class AutoSubscriptingMiddleware:
    def pre_response(self, result_dict, root_node):
        return result_dict[root_node._nodes[0]._operation_type]


class AddictMiddleware:
    def pre_response(self, result_dict, root_node):
        try:
            import addict  # type: ignore
            return addict.Dict(result_dict)
        except ImportError:
            raise Exception("addict not available")
