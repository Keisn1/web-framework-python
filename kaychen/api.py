import inspect
import os

from jinja2 import Environment, FileSystemLoader
from parse import parse
from requests import Session as RequestsSession
from webob import Request
from whitenoise import WhiteNoise
from wsgiadapter import WSGIAdapter as RequestsWSGIAdapter

from .middleware import Middleware
from .response import CustomResponse as Response


class API:
    def __init__(self, templates_dir="templates", static_dir="static"):
        self.routes = {}

        self.exception_handler = None

        self.templates_env = Environment(
            loader=FileSystemLoader(os.path.abspath(templates_dir))
        )

        self.whitenoise = WhiteNoise(self.wsgi_app, root=static_dir)
        self.middleware = Middleware(self)

    def __call__(self, environ, start_response):
        path_info = environ["PATH_INFO"]
        if path_info.startswith("/static"):
            environ["PATH_INFO"] = path_info[len("/static") :]
            return self.whitenoise(environ, start_response)

        return self.middleware(environ, start_response)

    def wsgi_app(self, environ, start_response):
        request = Request(environ)
        response = self.handle_request(request)
        return response(environ, start_response)

    def template(self, template_name: str, context: dict):
        return self.templates_env.get_template(template_name).render(context)

    def route(self, path, allowed_methods=None):
        def wrapper(handler):
            self.add_route(path, handler, allowed_methods)

        return wrapper

    def add_route(self, path, handler, allowed_methods=None):
        assert path not in self.routes, "Such route already exists"

        if allowed_methods is None:
            allowed_methods = ["get", "post", "put", "patch", "delete", "options"]

        self.routes[path] = {"handler": handler, "allowed_methods": allowed_methods}

    def add_exception_handler(self, exception_handler):
        self.exception_handler = exception_handler

    def handle_request(self, request: Request) -> Response:
        response = Response()

        handler_data, kwargs = self.find_handler(request.path)
        try:
            if handler_data is not None:
                if request.method.lower() not in handler_data["allowed_methods"]:
                    raise AttributeError("Method not allowed", request.method)

                handler = handler_data["handler"]
                if inspect.isclass(handler):
                    handler = getattr(handler(), request.method.lower(), None)
                    if handler is None:
                        raise AttributeError("Method not allowed", request.method)
                    handler(request, response, **kwargs)
                handler(request, response, **kwargs)
            else:
                self.default_response(response)

        except Exception as e:
            if self.exception_handler is None:
                raise e
            else:
                self.exception_handler(request, response, e)
        return response

    def find_handler(self, request_path: str):
        for path, handler_data in self.routes.items():
            res = parse(path, request_path)
            if res is not None:
                return handler_data, res.named
        return None, None

    def default_response(self, response: Response):
        response.status_code = 404
        response.text = "Not found"

    def test_session(self, base_url="http://testserver"):
        session = RequestsSession()
        session.mount(prefix=base_url, adapter=RequestsWSGIAdapter(self))
        return session

    def add_middleware(self, mid: type[Middleware]):
        self.middleware.add(mid)
