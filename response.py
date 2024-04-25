from typing import Iterable
from webob import Response
from wsgiref.types import WSGIEnvironment, StartResponse
import json


class CustomResponse:
    def __init__(self):
        self.json = None
        self.content_type = None
        self.status_code = 200
        self.body = ""
        self.html = None
        self.text = None

    def __call__(
        self, environ: WSGIEnvironment, start_response: StartResponse
    ) -> Iterable[bytes]:
        self.set_body_and_content_type()

        response = Response(
            body=self.body, content_type=self.content_type, status=f"{self.status_code}"
        )
        return response(environ, start_response)

    def set_body_and_content_type(self):
        if self.json is not None:
            self.body = json.dumps(self.json).encode("UTF-8")
            self.content_type = "application/json"

        if self.html is not None:
            self.content_type = "text/html"
            self.body = self.html.encode()

        if self.text is not None:
            self.body = self.text
            self.content_type = "text/plain"
