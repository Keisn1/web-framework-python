
# Table of Contents

1.  [Introduction](#org84350f7)
2.  [Part 1](#org11f8dc2)
    1.  [WSGI](#org18b0281)
        1.  [What is WSGI](#org2ed9c41)
        2.  [Application side](#org1e487d1)
    2.  [Routing](#org839bbed)
    3.  [Unit test and test client](#orge64aaf5)
    4.  [Templates](#org9bf5396)
    5.  [Static Files](#org99d371a)
    6.  [Middleware](#orge8c3ad4)
        1.  [The middleware class, base functionality](#org00ccee8)
        2.  [the convoluted part](#orga262db2)
        3.  [static files](#org85af68d)
    7.  [allowing methods](#org012d474)
    8.  [Custom Responses](#org6d40a1a)
    9.  [Pypi](#org9e31312)
    10. [example web app](#org34fd608)
    11. [Deploying to Heroku](#orgfaa2745)
        1.  [workflow](#org4eac52b)
        2.  [other heroku commands](#orgb444b69)
3.  [Part 2 - ORM](#org453f4aa)
    1.  [Design](#org6cff244)
        1.  [Connection](#orgfb0cb3b)
        2.  [table definition](#orgdab6ee0)
        3.  [creating tables](#orgc514403)
        4.  [inserting data](#orgf99dcc3)
        5.  [fetch all data](#org41789e9)
        6.  [query](#org0400e4c)
        7.  [save object with foreign key reference](#orgb2485a4)
        8.  [fetch object with foreign key reference](#orgf7223a1)
        9.  [update an object](#org9da5e24)
        10. [delete an object](#org75ffd39)

[\![label](https://img.shields.io/badge/label-message-color.svg)](https://img.shields.io/badge/label-message-color.svg)


<a id="org84350f7"></a>

# Introduction

This Repo follows the course &ldquo;Building your own Python Framework&rdquo; over at testdriven.io.
Over this course we learn about **WSGI** , how frameworks like **Django** and **Flask** implement their route functionality and other features like

-   templates
-   exception handling
-   middleware
-   allowing methods

and additionally about building your own **ORM** and **Deployment**.


<a id="org11f8dc2"></a>

# Part 1


<a id="org18b0281"></a>

## WSGI


<a id="org2ed9c41"></a>

### What is WSGI

WSGI (Web Server Gateway Interface) is a proposed standard as of PEP333 of how a Web Server should talk to a python web appilcation.

This gives way for a unified way of talking to python web applications for web servers, which in turn permits to deploy python web applications in a standardized way.


<a id="org1e487d1"></a>

### Application side

On the application side, we have the application object, which shall be callable and take 2 positional arguments

    def simple_app(environ, start_response):

It shall return an iterable yielding zero or more strings

This application can then be served e.g. with gunicorn or for development purposes with `wsgiref.simple_server`

    from wsgiref.simple_server import make_server
    
    server = make_server('localhost', 8000, app=simple_app)
    server.serve_forever()


<a id="org839bbed"></a>

## Routing

To acheive Decorator like registering of routes like in **Flask** or injection-like registering like in **Django**, one needs to implement a method on its application object for registering the routes. The application can make use of the [Parse](https://github.com/r1chardj0n3s/parse) library to easily retrieve the routes via route-patterns

    def add_route(self, path, handler):
        assert path not in self.routes, "Such route already exists"
        self.routes[path] = handler
    
    def find_handler(self, request_path: str):
        for path, handler in self.routes.items():
            res = parse(path, request_path)

For easier and more intuitive handling of `environ` and `start_response` one can use [webob](https://docs.pylonsproject.org/projects/webob/en/stable/index.html) Request and Response objects.


<a id="orge64aaf5"></a>

## Unit test and test client

Using unit test one can verify the base functionality.
For extending the functionality like default-responses, templates, exception handlers and static files, we write the tests first, see them fail and add the functionality itself, followed by refactoring.

To test the app in an fast, isolated and repeatable way, one would need a test<sub>client</sub> to call the api without spinning it up with a web server each time. This can be acheive using the [request-wsgi-adapter](https://github.com/seanbrant/requests-wsgi-adapter).

    def test_session(self, base_url="http://testserver"):
        session = RequestsSession()
        session.mount(prefix=base_url, adapter=RequestsWSGIAdapter(self))
        return session


<a id="org9bf5396"></a>

## Templates

Templates are as easy as providing the templates<sub>dir</sub> on app initialization and using it inside the route

    def __init__(self, templates_dir="templates"):
        self.routes = {}
        self.templates_env = Environment(
            loader=FileSystemLoader(os.path.abspath(templates_dir))
        )
    
    def template(self, template_name: str, context: dict):
        return self.templates_env.get_template(template_name).render(context)
    
    @app.route("/html")
    def html_handler(req, resp):
        resp.body = app.template(
            "home.html", context={"title": "Some Title", "name": "Some Name"}
        ).encode()


<a id="org99d371a"></a>

## Static Files

To use static files we make use of the package Whitenoise.
Whitenoise wraps a wsgi-application and provides it with static files.
Since a wsgi application is just a callable with a specific function signature, we can wrap whatever we had inside the `__call__` method
of our API class, and call that with whitenoise.

    def __init__(self, templates_dir="templates", static_dir="static"):
        self.whitenoise = WhiteNoise(self.wsgi_app, root=static_dir)
        ...
    def __call__(self, environ, start_response):
        return self.whitenoise(environ, start_response)


<a id="orge8c3ad4"></a>

## Middleware


<a id="org00ccee8"></a>

### The middleware class, base functionality

To use middleware, we write a Class `Middleware`. It defines two methods to process request and response: `process_request` and `process_response`.
These functions do nothing on the base class, but can be overwritten when creating a child.

When handling requests, it first calls process<sub>request</sub>, then the handler of the app, then the process<sub>response</sub>, before returning the response.

    class Middleware:
        ...
        def handle_request(self, request):
            self.process_request(request)
            response = self.app.handle_request(request)
            self.process_response(request)
            return response

Since each middleware serves as the Server-side implementation of the WSGI protocol for the application that gets called after it, it needs to be callable in the WSGI sense.

    class Middleware:
        ...
        def __call__(self, environ, start_response):
            request = Request(environ)
            response = Response(self.handle_request)
            return response(environ, start_response)

The wsgi logic of using environ and start<sub>response</sub> is hidden in the behavior of the webob objects Request and Response.


<a id="orga262db2"></a>

### the convoluted part

Furthermore, to add another middleware to the middleware stack, one wraps a given middleware aroung the app.

    class Middleware:
        ...
        def add(mid: Middleware):
            self.app = mid(self.app)

We can then apply the same logic on our framework api, by initialising a base middleware with our app, and calling the middleware when handling requests

    class API:
        def __init__(self, templates_dir="templates", static_dir="static"):
            ...
            self.mid = Middleware(self)
    
        ...
    
        def add(mid: Middleware):
            self.app = mid(self.app)
    
        ...
    
        def __call__(self, environ, start_response):
            self.middleware(environ, start_response)


<a id="org85af68d"></a>

### static files

This would unable our handling of static files. Therefore we oblige to be the static files being served on route, which root is `/static`

    def __call__(self, environ, start_response):
        path_info = environ["PATH_INFO"]
        if path_info.startswith("/static"):
            environ["PATH_INFO"] = path_info[len("/static") :]
            return self.whitenoise(environ, start_response)
    
        return self.middleware(environ, start_response)


<a id="org012d474"></a>

## allowing methods

Adding allowed methods to all our ways of adding routes, requires us to change our data structure a little bit.
From

    self.routes[path] = handler

to

    self.routes[path] = {"handler": handler, "allowed_methods": allowed_methods}

Which we then can exploit when we&rsquo;re handling the request

    ...
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
    ...


<a id="org6d40a1a"></a>

## Custom Responses

Next we make it possible to respond with json, html or plain text.
Therefore one may implement a Custom Response that makes use of the Webob Response object.
The user has access to that response object via the handler (as before).

    @app.route("/home")
    def html(req, resp):
        resp.json = {"name": "kaychen"}

When the framework sends back the response, as in

    def handle_request(self, request):
        response = CustomResponse
        ...
        return response()

the response call method is executed. This is where the logic is applied then

    from webob import Response
    
    def CustomResponse:
        self.json = None
        self.status_code = 200
        ...                         # setting of other variables
    
       def __call__(self):
           self.set_body_and_content_type()
           response = Response(
               body=self.body, content_type=self.content_type, status=f"{self.status_code}"
           )
           return response(environ, start_response)
    
        def set_body_and_content_type(self):
            if self.json is not None:
                self.body = json.dumps(self.json).encode("UTF-8")
                self.content_type = "application/json"
            ...                     # more handling of html and text


<a id="org9e31312"></a>

## Pypi

Next we publish the package to Pypi using [setup.py (for humans)](https://github.com/navdeep-G/setup.py). A few things to keep in mind

-   `find_packages` used in setup.py, therefore need to have `__init__.py` so it finds the package
-   when using the package in combination with `gunicorn`, one still needs to install `gunicorn` inside the virtualenv
-   need to create directories (`/static`, `/templates`)


<a id="org34fd608"></a>

## example web app

To see the framework in action we build an example application: [kaychen-web-app](https://github.com/Keisn1/kaychen-web-app)


<a id="orgfaa2745"></a>

## Deploying to Heroku


<a id="org4eac52b"></a>

### workflow

1.  Define Procfile
2.  `heroku create`
    -   git remote is create alongside the app on heroku account
    -   deplying via git push
3.  `git push heroku main`
4.  Check if application is deployed: `heroku ps:scale web=1`
5.  View logs: `heroku logs --tail`
6.  


<a id="orgb444b69"></a>

### other heroku commands

1.  Scaling = number of running dynos (lightweight container) `heroku ps:scale web={number_of_dynos}`


<a id="org453f4aa"></a>

# Part 2 - ORM

ORMs allow you to

1.  interact wiht db in own language of choice
2.  abstract away the database (easy switching)
3.  Usually written by SQL experts for performance reasons


<a id="org6cff244"></a>

## Design


<a id="orgfb0cb3b"></a>

### Connection

    from kaychen import Database
    
    db = Database("./test.db")


<a id="orgdab6ee0"></a>

### table definition

    from kaychen import Table, Column, ForeignKey
    
    class Author(Table):
        name = Column(str)
        age = Column(int)
    
    class Book(Table):
        title = Column(str)
        published = Column(bool)
        author = ForeignKey(Author)


<a id="orgc514403"></a>

### creating tables

    db.create(Author)
    db.create(Book)


<a id="orgf99dcc3"></a>

### inserting data

    kay = Author("Kay", age=12)
    db.insert(kay)


<a id="org41789e9"></a>

### fetch all data

    authors = db.all(Author)


<a id="org0400e4c"></a>

### query

    author = db.query(Author, 47)


<a id="orgb2485a4"></a>

### save object with foreign key reference

    book = Book(title="Building an ORM", published=True, author=greg)
    db.save(book)


<a id="orgf7223a1"></a>

### fetch object with foreign key reference

    print(Book.get(55).author.name)


<a id="org9da5e24"></a>

### update an object

    book.title = "How to build an ORM"
    db.update(book)


<a id="org75ffd39"></a>

### delete an object

    db.delete(Book, id=book.id)

