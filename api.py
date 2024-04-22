from webob import Request, Response
from parse import parse
import inspect


class API:
    def __init__(self):
        self.routes = {}

    def __call__(self, environ, start_response):
        request = Request(environ)
        response = self.handle_request(request)
        return response(environ, start_response)

    def route(self, path):
        assert path not in self.routes, "Such route already exists"

        def wrapper(handler):
            self.routes[path] = handler

        return wrapper

    def handle_request(self, request: Request) -> Response:
        response = Response()

        handler, kwargs = self.find_handler(request.path)

        if handler is not None:
            if inspect.isclass(handler):
                handler = getattr(handler(), request.method.lower(), None)
                if handler is None:
                    raise AttributeError("Method not allowed", request.method)
            handler(request, response, **kwargs)
            return response

        self.default_response(response)
        return response

    def find_handler(self, request_path: str):
        for path, handler in self.routes.items():
            res = parse(path, request_path)
            if res is not None:
                return handler, res.named
        return None, None

    def default_response(self, response: Response):
        response.status_code = 404
        response.text = "Not found"
