
# Table of Contents

1.  [Introduction](#orgcbf3ee4)
2.  [Part 1](#orge656e01)
    1.  [WSGI](#orgc0538b9)
        1.  [What is WSGI](#orgf20f575)
        2.  [Application side](#orgc8b3854)
    2.  [Routing](#org54117a7)
    3.  [Unit test and test client](#orgcd0162e)
    4.  [Templates](#org6a9eafe)
    5.  [Static Files](#orgb2f8ce7)
    6.  [Middleware](#org174fadf)
        1.  [The middleware class, base functionality](#org25cae3a)
        2.  [the convoluted part](#org826d7a2)
        3.  [static files](#orgd1bd72e)
    7.  [allowing methods](#org0c5f995)
    8.  [Custom Responses](#orgeccbed9)
    9.  [Pypi](#org5dfc811)
    10. [example web app](#orgc3e2ef8)
    11. [Deploying to Heroku](#org9fbf038)
        1.  [workflow](#org3383b53)
        2.  [other heroku commands](#orge4dbcca)
3.  [Part 2 - ORM](#org27db4e8)
    1.  [Design](#org2d5265e)
        1.  [Connection](#org5fb5daa)
        2.  [table definition](#orgf8f93f3)
        3.  [creating tables](#orge217562)
        4.  [inserting data](#org707623f)
        5.  [fetch all data](#org6933468)
        6.  [query](#org47d8a3a)
        7.  [save object with foreign key reference](#org67333f5)
        8.  [fetch object with foreign key reference](#org2adb142)
        9.  [update an object](#org57d0362)
        10. [delete an object](#org2f5ffa6)

[\![purpos](https://img.shields.io/badge/purpose-learning-green.svg)](https://img.shields.io/badge/purpose-learning-green.svg)
[purpose]
[[https://img.shields.io/pypi/v/bumbo.svg][Pypi](https://img.shields.io/badge/purpose-learning-green.svg)


<a id="orgcbf3ee4"></a>

# Introduction

This Repo follows the course &ldquo;Building your own Python Framework&rdquo; over at testdriven.io.
Over this course we learn about **WSGI** , how frameworks like **Django** and **Flask** implement their route functionality and other features like

-   templates
-   exception handling
-   middleware
-   allowing methods

and additionally about building your own **ORM** and **Deployment**.


<a id="orge656e01"></a>

# Part 1


<a id="orgc0538b9"></a>

## WSGI


<a id="orgf20f575"></a>

### What is WSGI

WSGI (Web Server Gateway Interface) is a proposed standard as of PEP333 of how a Web Server should talk to a python web appilcation.

This gives way for a unified way of talking to python web applications for web servers, which in turn permits to deploy python web applications in a standardized way.


<a id="orgc8b3854"></a>

### Application side

On the application side, we have the application object, which shall be callable and take 2 positional arguments

    def simple_app(environ, start_response):

It shall return an iterable yielding zero or more strings

This application can then be served e.g. with gunicorn or for development purposes with `wsgiref.simple_server`

    from wsgiref.simple_server import make_server
    
    server = make_server('localhost', 8000, app=simple_app)
    server.serve_forever()


<a id="org54117a7"></a>

## Routing

To acheive Decorator like registering of routes like in **Flask** or injection-like registering like in **Django**, one needs to implement a method on its application object for registering the routes. The application can make use of the [Parse](https://github.com/r1chardj0n3s/parse) library to easily retrieve the routes via route-patterns

    def add_route(self, path, handler):
        assert path not in self.routes, "Such route already exists"
        self.routes[path] = handler
    
    def find_handler(self, request_path: str):
        for path, handler in self.routes.items():
            res = parse(path, request_path)

For easier and more intuitive handling of `environ` and `start_response` one can use [webob](https://docs.pylonsproject.org/projects/webob/en/stable/index.html) Request and Response objects.


<a id="orgcd0162e"></a>

## Unit test and test client

Using unit test one can verify the base functionality.
For extending the functionality like default-responses, templates, exception handlers and static files, we write the tests first, see them fail and add the functionality itself, followed by refactoring.

To test the app in an fast, isolated and repeatable way, one would need a test<sub>client</sub> to call the api without spinning it up with a web server each time. This can be acheive using the [request-wsgi-adapter](https://github.com/seanbrant/requests-wsgi-adapter).

    def test_session(self, base_url="http://testserver"):
        session = RequestsSession()
        session.mount(prefix=base_url, adapter=RequestsWSGIAdapter(self))
        return session


<a id="org6a9eafe"></a>

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


<a id="orgb2f8ce7"></a>

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


<a id="org174fadf"></a>

## Middleware


<a id="org25cae3a"></a>

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


<a id="org826d7a2"></a>

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


<a id="orgd1bd72e"></a>

### static files

This would unable our handling of static files. Therefore we oblige to be the static files being served on route, which root is `/static`

    def __call__(self, environ, start_response):
        path_info = environ["PATH_INFO"]
        if path_info.startswith("/static"):
            environ["PATH_INFO"] = path_info[len("/static") :]
            return self.whitenoise(environ, start_response)
    
        return self.middleware(environ, start_response)


<a id="org0c5f995"></a>

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


<a id="orgeccbed9"></a>

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


<a id="org5dfc811"></a>

## Pypi

Next we publish the package to Pypi using [setup.py (for humans)](https://github.com/navdeep-G/setup.py). A few things to keep in mind

-   `find_packages` used in setup.py, therefore need to have `__init__.py` so it finds the package
-   when using the package in combination with `gunicorn`, one still needs to install `gunicorn` inside the virtualenv
-   need to create directories (`/static`, `/templates`)


<a id="orgc3e2ef8"></a>

## example web app

To see the framework in action we build an example application: [kaychen-web-app](https://github.com/Keisn1/kaychen-web-app)


<a id="org9fbf038"></a>

## Deploying to Heroku


<a id="org3383b53"></a>

### workflow

1.  Define Procfile
2.  `heroku create`
    -   git remote is create alongside the app on heroku account
    -   deplying via git push
3.  `git push heroku main`
4.  Check if application is deployed: `heroku ps:scale web=1`
5.  View logs: `heroku logs --tail`
6.  


<a id="orge4dbcca"></a>

### other heroku commands

1.  Scaling = number of running dynos (lightweight container) `heroku ps:scale web={number_of_dynos}`


<a id="org27db4e8"></a>

# Part 2 - ORM

ORMs allow you to

1.  interact wiht db in own language of choice
2.  abstract away the database (easy switching)
3.  Usually written by SQL experts for performance reasons


<a id="org2d5265e"></a>

## Design


<a id="org5fb5daa"></a>

### Connection

    from kaychen import Database
    
    db = Database("./test.db")


<a id="orgf8f93f3"></a>

### table definition

    from kaychen import Table, Column, ForeignKey
    
    class Author(Table):
        name = Column(str)
        age = Column(int)
    
    class Book(Table):
        title = Column(str)
        published = Column(bool)
        author = ForeignKey(Author)


<a id="orge217562"></a>

### creating tables

    db.create(Author)
    db.create(Book)


<a id="org707623f"></a>

### inserting data

    kay = Author("Kay", age=12)
    db.insert(kay)


<a id="org6933468"></a>

### fetch all data

    authors = db.all(Author)


<a id="org47d8a3a"></a>

### query

    author = db.query(Author, 47)


<a id="org67333f5"></a>

### save object with foreign key reference

    book = Book(title="Building an ORM", published=True, author=greg)
    db.save(book)


<a id="org2adb142"></a>

### fetch object with foreign key reference

    print(Book.get(55).author.name)


<a id="org57d0362"></a>

### update an object

    book.title = "How to build an ORM"
    db.update(book)


<a id="org2f5ffa6"></a>

### delete an object

    db.delete(Book, id=book.id)

