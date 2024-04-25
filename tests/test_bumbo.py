import pathlib

import pytest
import requests

from kaychen.api import API
from kaychen.middleware import Middleware


def test_template_inside_handler(app: API, test_client: requests.Session):
    @app.route("/html")
    def html_handler(req, resp):
        resp.body = app.template(
            "home.html", context={"title": "Some Title", "name": "Some Name"}
        ).encode()

    response = test_client.get("http://testserver/html")

    assert "text/html" in response.headers["Content-Type"]
    assert "Some Title" in response.text
    assert "Some Name" in response.text


def test_template(app: API, test_client: requests.Session):
    body = app.template(
        "home.html", context={"title": "Some Title", "name": "Some Name"}
    )

    assert "Some Title" in body
    assert "Some Name" in body


def test_basic_django_like_route_adding(app: API, test_client: requests.Session):
    def add(request, response):
        response.text = "Hello from add"

    app.add_route("/add", add)
    assert test_client.get("http://testserver/add").text == "Hello from add"


def test_basic_route_adding(app: API, test_client: requests.Session):
    @app.route("/add")
    def add(request, response):
        response.text = "Hello from add"

    assert test_client.get("http://testserver/add").text == "Hello from add"


def test_route_overlap_throws_exception(app: API):
    @app.route("/add")
    def add(request, response):
        return "Hello from add"

    with pytest.raises(AssertionError):

        @app.route("/add")
        def add2(request, response):
            return "Hello from add2"


def test_404_response(test_client: requests.Session):
    assert test_client.get("http://testserver/notFound").status_code == 404


def test_basic_route_adding_with_parameters(app: API, test_client: requests.Session):
    @app.route("/{name}")
    def add(request, response, name):
        response.text = f"Hello from {name}"

    assert test_client.get("http://testserver/carla").text == "Hello from carla"


def test_class_based_handler_get(app: API, test_client: requests.Session):
    response_text = "this is a get request"

    @app.route("/book")
    class BookResource:
        def get(self, req, resp):
            resp.text = response_text

    assert test_client.get("http://testserver/book").text == response_text


def test_class_based_handler_post(app: API, test_client: requests.Session):
    response_text = "this is a post request"

    @app.route("/book")
    class BookResource:
        def post(self, req, resp):
            resp.text = response_text

    assert test_client.post("http://testserver/book").text == response_text


def test_class_based_handler_not_allowed_method(
    app: API, test_client: requests.Session
):
    @app.route("/book")
    class BookResource:
        def post(self, req, resp):
            resp.text = "yolo"

    with pytest.raises(AttributeError):
        test_client.get("http://testserver/book")


def test_class_based_handler_not_allowed_method_post(
    app: API, test_client: requests.Session
):
    @app.route("/book")
    class BookResource:
        def get(self, req, resp):
            resp.text = "yolo"

    with pytest.raises(AttributeError):
        test_client.post("http://testserver/book")


def test_custom_exception_handler(app: API, test_client: requests.Session):
    def on_exception(req, resp, exc):
        resp.text = "AttributeErrorHappened"

    app.add_exception_handler(on_exception)

    @app.route("/")
    def index(req, resp):
        print("hello")
        raise AttributeError()

    response = test_client.get("http://testserver/")
    assert response.text == "AttributeErrorHappened"


def test_404_is_returned_for_nonexistent_static_file(test_client: requests.Session):
    assert test_client.get(f"http://testserver/static/main.css)").status_code == 404


FILE_DIR = "css"
FILE_NAME = "main.css"
FILE_CONTENTS = "body {background-color: red}"


def _create_static(static_dir: pathlib.Path):
    (static_dir / FILE_DIR).mkdir()
    asset = static_dir / FILE_DIR / FILE_NAME
    asset.write_text(FILE_CONTENTS, encoding="utf-8")
    return asset


def test_assets_are_served(tmp_path_factory: pytest.TempPathFactory):
    static_dir = tmp_path_factory.mktemp("static")
    _create_static(static_dir)

    api = API(static_dir=str(static_dir))

    test_client = api.test_session()

    response = test_client.get(f"http://testserver/static/{FILE_DIR}/{FILE_NAME}")

    assert response.status_code == 200
    assert response.text == FILE_CONTENTS


def test_returns_for_nonexistent_static_file(test_client: requests.Session):
    assert test_client.get(f"http://testserver/main.css)").status_code == 404


def test_adding_middleware(app: API, test_client: requests.Session):
    process_request_called = False
    process_response_called = False

    class CallMiddlewareMethods(Middleware):
        def __init__(self, app):
            super().__init__(app)

        def process_request(self, req):
            nonlocal process_request_called
            process_request_called = True

        def process_response(self, req, res):
            nonlocal process_response_called
            process_response_called = True

    app.add_middleware(CallMiddlewareMethods)

    @app.route("/")
    def index(req, res):
        res.text = "YOLO"

    test_client.get("http://testserver/")

    assert process_request_called is True
    assert process_response_called is True


def test_allowed_methods_for_function_based_handlers(
    app: API, test_client: requests.Session
):
    @app.route("/home", allowed_methods=["post"])
    def home(req, resp):
        resp.text = "Hello"

    with pytest.raises(AttributeError):
        test_client.get("http://testserver/home")
    assert test_client.post("http://testserver/home").text == "Hello"


def test_json_response_helper(app: API, test_client: requests.Session):
    @app.route("/json")
    def json_handler(req, resp):
        resp.json = {"name": "bubmo"}

    response = test_client.get("http://testserver/json")
    json_body = response.json()

    assert response.headers["Content-Type"] == "application/json"
    assert json_body["name"] == "bubmo"


def test_html_response_helper(app: API, test_client: requests.Session):
    @app.route("/html")
    def html_handler(req, resp):
        resp.html = app.template(
            "index.html", context={"title": "Best Title", "name": "Best Name"}
        )

    response = test_client.get("http://testserver/html")

    assert "text/html" in response.headers["Content-Type"]
    assert "Best Title" in response.text
    assert "Best Name" in response.text


def test_text_response_helper(app: API, test_client: requests.Session):
    response_text = "Just Plain Text"

    @app.route("/text")
    def text_handler(req, resp):
        resp.text = response_text
        pass

    response = test_client.get("http://testserver/text")
    assert "text/plain" in response.headers["Content-Type"]
    assert response.text == response_text


def test_manually_setting_body(app: API, test_client: requests.Session):
    @app.route("/body")
    def text_handler(req, resp):
        resp.body = b"Byte Body"
        resp.content_type = "text/plain"

    response = test_client.get("http://testserver/body")

    assert "text/plain" in response.headers["Content-Type"]
    assert response.text == "Byte Body"
