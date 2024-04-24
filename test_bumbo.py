import pytest
import requests
from api import API
import pathlib


def test_template_inside_handler(api: API, test_client: requests.Session):
    @api.route("/html")
    def html_handler(req, resp):
        resp.body = api.template(
            "home.html", context={"title": "Some Title", "name": "Some Name"}
        ).encode()

    response = test_client.get("http://testserver/html")

    assert "text/html" in response.headers["Content-Type"]
    assert "Some Title" in response.text
    assert "Some Name" in response.text


def test_template(api: API, test_client: requests.Session):
    body = api.template(
        "home.html", context={"title": "Some Title", "name": "Some Name"}
    )

    assert "Some Title" in body
    assert "Some Name" in body


def test_basic_django_like_route_adding(api: API, test_client: requests.Session):
    def add(request, response):
        response.text = "Hello from add"

    api.add_route("/add", add)
    assert test_client.get("http://testserver/add").text == "Hello from add"


def test_basic_route_adding(api: API, test_client: requests.Session):
    @api.route("/add")
    def add(request, response):
        response.text = "Hello from add"

    assert test_client.get("http://testserver/add").text == "Hello from add"


def test_route_overlap_throws_exception(api: API):
    @api.route("/add")
    def add(request, response):
        return "Hello from add"

    with pytest.raises(AssertionError):

        @api.route("/add")
        def add2(request, response):
            return "Hello from add2"


def test_404_response(test_client: requests.Session):
    assert test_client.get("http://testserver/notFound").status_code == 404


def test_basic_route_adding_with_parameters(api: API, test_client: requests.Session):
    @api.route("/{name}")
    def add(request, response, name):
        response.text = f"Hello from {name}"

    assert test_client.get("http://testserver/carla").text == "Hello from carla"


def test_class_based_handler_get(api: API, test_client: requests.Session):
    response_text = "this is a get request"

    @api.route("/book")
    class BookResource:
        def get(self, req, resp):
            resp.text = response_text

    assert test_client.get("http://testserver/book").text == response_text


def test_class_based_handler_post(api: API, test_client: requests.Session):
    response_text = "this is a post request"

    @api.route("/book")
    class BookResource:
        def post(self, req, resp):
            resp.text = response_text

    assert test_client.post("http://testserver/book").text == response_text


def test_class_based_handler_not_allowed_method(
    api: API, test_client: requests.Session
):
    @api.route("/book")
    class BookResource:
        def post(self, req, resp):
            resp.text = "yolo"

    with pytest.raises(AttributeError):
        test_client.get("http://testserver/book")


def test_class_based_handler_not_allowed_method_post(
    api: API, test_client: requests.Session
):
    @api.route("/book")
    class BookResource:
        def get(self, req, resp):
            resp.text = "yolo"

    with pytest.raises(AttributeError):
        test_client.post("http://testserver/book")


def test_custom_exception_handler(api: API, test_client: requests.Session):
    def on_exception(req, resp, exc):
        resp.text = "AttributeErrorHappened"

    api.add_exception_handler(on_exception)

    @api.route("/")
    def index(req, resp):
        print("hello")
        raise AttributeError()

    response = test_client.get("http://testserver/")
    assert response.text == "AttributeErrorHappened"


def test_404_is_returned_for_nonexistent_static_file(test_client: requests.Session):
    assert test_client.get(f"http://testserver/main.css)").status_code == 404


FILE_DIR = "css"
FILE_NAME = "main.css"
FILE_CONTENTS = "body {background-color: red}"


def _create_static(static_dir: pathlib.Path):
    asset = static_dir / FILE_NAME
    asset.write_text(FILE_CONTENTS, encoding="utf-8")
    return asset


def test_assets_are_served(tmp_path_factory: pytest.TempPathFactory):
    static_dir = tmp_path_factory.mktemp(FILE_DIR)
    _create_static(static_dir)

    api = API(static_dir=str(static_dir))

    test_client = api.test_session()

    response = test_client.get(f"http://testserver/{FILE_NAME}")

    assert response.status_code == 200
    assert response.text == FILE_CONTENTS


def test_returns_for_nonexistent_static_file(test_client: requests.Session):
    assert test_client.get(f"http://testserver/main.css)").status_code == 404
