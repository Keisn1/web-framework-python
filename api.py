from webob import Request, Response


class API:
    def __init__(self):
        self.routes = {}

    def __call__(self, environ, start_response):
        request = Request(environ)

        response = self.handle_request(request)

        return response(environ, start_response)

    def route(self, path):
        def wrapper(handler):
            self.routes[path] = handler

        return wrapper

    def handle_request(self, request) -> Response:
        response = Response()

        for path, handler in self.routes.items():
            if path == request.path:
                handler(request, response)

        return response
