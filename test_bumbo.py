import pytest
import requests
from api import API


def test_basic_route_adding(api, test_client: requests.Session):
    @api.route("/add")
    def add(request, response):
        response.text = "Hello from add"

    resp = test_client.get("http://testserver/add")
    assert resp.status_code == 200
    assert resp.text == "Hello from add"


def test_route_overlap_throws_exception(api):
    @api.route("/add")
    def add(request, response):
        return "Hello from add"

    with pytest.raises(AssertionError):

        @api.route("/add")
        def add2(request, response):
            return "Hello from add2"


def test_404_response(api, test_client: requests.Session):
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
