
# Table of Contents

1.  [Introduction](#org00b3404)
2.  [Table of contents](#org167f79a)
3.  [Part 1](#org728edfe)
    1.  [WSGI](#org8b7f183)
        1.  [What is WSGI](#org73adc25)
        2.  [Application side](#org79d7cad)
    2.  [Routing](#org8d41e2a)
    3.  [Unit test and test client](#orga6dc501)
    4.  [Templates](#org6bc4290)
    5.  [Static Files](#org680dae4)
    6.  [Middleware](#org281c0f2)
        1.  [The middleware class, base functionality](#orga7763d5)
        2.  [the convoluted part](#org8b50803)
        3.  [static files](#orgee628f1)
    7.  [allowing methods](#orgbb60c02)
    8.  [Custom Responses](#org9a7c918)
    9.  [Pypi](#orgbaf2e26)
    10. [example web app](#org9b0666c)
    11. [Deploying to Heroku](#org5792eb4)
        1.  [workflow](#orgb76ce49)
        2.  [other heroku commands](#org7f84520)
4.  [Part 2 - ORM](#org609f064)
    1.  [Design](#org62813a8)
        1.  [Connection](#org5942478)
        2.  [table definition](#org519bf13)
        3.  [creating tables](#org9cf86a2)
        4.  [inserting data](#org89b9e48)
        5.  [fetch all data](#orgf60b60b)
        6.  [query](#org2af1ed2)
        7.  [save object with foreign key reference](#orgea90492)
        8.  [fetch object with foreign key reference](#orgef7ddda)
        9.  [update an object](#org614ae6e)
        10. [delete an object](#org77e8892)
    2.  [Implementing the Database, Tables, Columns and ForeignKeys](#orge7d3161)

    ![purpose](https://img.shields.io/badge/purpose-learning-green.svg)
    ![PyPI](https://img.shields.io/pypi/v/bumbo.svg)


<a id="org00b3404"></a>

# Introduction

This Repo follows the course &ldquo;Building your own Python Framework&rdquo; over at testdriven.io.
Over this course we learn about **WSGI** , how frameworks like **Django** and **Flask** implement their route functionality and other features like

-   templates
-   exception handling
-   middleware
-   allowing methods

and additionally about building your own **ORM** and **Deployment**.


<a id="org167f79a"></a>

# Table of contents


# Table of Contents

1.  [Introduction](#org00b3404)
2.  [Table of contents](#org167f79a)
3.  [Part 1](#org728edfe)
    1.  [WSGI](#org8b7f183)
    2.  [Routing](#org8d41e2a)
    3.  [Unit test and test client](#orga6dc501)
    4.  [Templates](#org6bc4290)
    5.  [Static Files](#org680dae4)
    6.  [Middleware](#org281c0f2)
    7.  [allowing methods](#orgbb60c02)
    8.  [Custom Responses](#org9a7c918)
    9.  [Pypi](#orgbaf2e26)
    10. [example web app](#org9b0666c)
    11. [Deploying to Heroku](#org5792eb4)
4.  [Part 2 - ORM](#org609f064)
    1.  [Design](#org62813a8)
    2.  [Implementing the Database, Tables, Columns and ForeignKeys](#orge7d3161)


<a id="org728edfe"></a>

# Part 1


<a id="org8b7f183"></a>

## WSGI


<a id="org73adc25"></a>

### What is WSGI

WSGI (Web Server Gateway Interface) is a proposed standard as of PEP333 of how a Web Server should talk to a python web appilcation.

This gives way for a unified way of talking to python web applications for web servers, which in turn permits to deploy python web applications in a standardized way.


<a id="org79d7cad"></a>

### Application side

On the application side, we have the application object, which shall be callable and take 2 positional arguments

    def simple_app(environ, start_response):

It shall return an iterable yielding zero or more strings

This application can then be served e.g. with gunicorn or for development purposes with `wsgiref.simple_server`

    from wsgiref.simple_server import make_server
    
    server = make_server('localhost', 8000, app=simple_app)
    server.serve_forever()


<a id="org8d41e2a"></a>

## Routing

To acheive Decorator like registering of routes like in **Flask** or injection-like registering like in **Django**, one needs to implement a method on its application object for registering the routes. The application can make use of the [Parse](https://github.com/r1chardj0n3s/parse) library to easily retrieve the routes via route-patterns

    def add_route(self, path, handler):
        assert path not in self.routes, "Such route already exists"
        self.routes[path] = handler
    
    def find_handler(self, request_path: str):
        for path, handler in self.routes.items():
            res = parse(path, request_path)

For easier and more intuitive handling of `environ` and `start_response` one can use [webob](https://docs.pylonsproject.org/projects/webob/en/stable/index.html) Request and Response objects.


<a id="orga6dc501"></a>

## Unit test and test client

Using unit test one can verify the base functionality.
For extending the functionality like default-responses, templates, exception handlers and static files, we write the tests first, see them fail and add the functionality itself, followed by refactoring.

To test the app in an fast, isolated and repeatable way, one would need a test<sub>client</sub> to call the api without spinning it up with a web server each time. This can be acheive using the [request-wsgi-adapter](https://github.com/seanbrant/requests-wsgi-adapter).

    def test_session(self, base_url="http://testserver"):
        session = RequestsSession()
        session.mount(prefix=base_url, adapter=RequestsWSGIAdapter(self))
        return session


<a id="org6bc4290"></a>

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


<a id="org680dae4"></a>

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


<a id="org281c0f2"></a>

## Middleware


<a id="orga7763d5"></a>

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


<a id="org8b50803"></a>

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


<a id="orgee628f1"></a>

### static files

This would unable our handling of static files. Therefore we oblige to be the static files being served on route, which root is `/static`

    def __call__(self, environ, start_response):
        path_info = environ["PATH_INFO"]
        if path_info.startswith("/static"):
            environ["PATH_INFO"] = path_info[len("/static") :]
            return self.whitenoise(environ, start_response)
    
        return self.middleware(environ, start_response)


<a id="orgbb60c02"></a>

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


<a id="org9a7c918"></a>

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


<a id="orgbaf2e26"></a>

## Pypi

Next we publish the package to Pypi using [setup.py (for humans)](https://github.com/navdeep-G/setup.py). A few things to keep in mind

-   `find_packages` used in setup.py, therefore need to have `__init__.py` so it finds the package
-   when using the package in combination with `gunicorn`, one still needs to install `gunicorn` inside the virtualenv
-   need to create directories (`/static`, `/templates`)


<a id="org9b0666c"></a>

## example web app

To see the framework in action we build an example application: [kaychen-web-app](https://github.com/Keisn1/kaychen-web-app)


<a id="org5792eb4"></a>

## Deploying to Heroku


<a id="orgb76ce49"></a>

### workflow

1.  Define Procfile
2.  `heroku create`
    -   git remote is create alongside the app on heroku account
    -   deplying via git push
3.  `git push heroku main`
4.  Check if application is deployed: `heroku ps:scale web=1`
5.  View logs: `heroku logs --tail`
6.  


<a id="org7f84520"></a>

### other heroku commands

1.  Scaling = number of running dynos (lightweight container) `heroku ps:scale web={number_of_dynos}`


<a id="org609f064"></a>

# Part 2 - ORM

ORMs allow you to

1.  interact wiht db in own language of choice
2.  abstract away the database (easy switching)
3.  Usually written by SQL experts for performance reasons


<a id="org62813a8"></a>

## Design


<a id="org5942478"></a>

### Connection

    from kaychen import Database
    
    db = Database("./test.db")


<a id="org519bf13"></a>

### table definition

    from kaychen import Table, Column, ForeignKey
    
    class Author(Table):
        name = Column(str)
        age = Column(int)
    
    class Book(Table):
        title = Column(str)
        published = Column(bool)
        author = ForeignKey(Author)


<a id="org9cf86a2"></a>

### creating tables

    db.create(Author)
    db.create(Book)


<a id="org89b9e48"></a>

### inserting data

    kay = Author("Kay", age=12)
    db.insert(kay)


<a id="orgf60b60b"></a>

### fetch all data

    authors = db.all(Author)


<a id="org2af1ed2"></a>

### query

    author = db.query(Author, 47)


<a id="orgea90492"></a>

### save object with foreign key reference

    book = Book(title="Building an ORM", published=True, author=greg)
    db.save(book)


<a id="orgef7ddda"></a>

### fetch object with foreign key reference

    print(Book.get(55).author.name)


<a id="org614ae6e"></a>

### update an object

    book.title = "How to build an ORM"
    db.update(book)


<a id="org77e8892"></a>

### delete an object

    db.delete(Book, id=book.id)


<a id="orge7d3161"></a>

## Implementing the Database, Tables, Columns and ForeignKeys

The database holds primarily a database connection and has the ability to create new tables.
Furthermore it has the ability to print the tables. Create and print tables are wrappers for executing sql commands.

    class Database:
        def __init__(self, path: str):
            self.conn = sqlite3.Connection(path)
    
        def create(self, table: type[Table]):
            self.conn.execute(table._get_create_sql())
    
        @property
        def tables(self) -> list[type[Table]]:
            SELECT_TABLES_SQL = "SELECT name FROM sqlite_master WHERE type = 'table';"
            return [x[0] for x in self.conn.execute(SELECT_TABLES_SQL).fetchall()]

It is only the database that executes sql commands via its db connection.
Other objects may provide the Database with how it should query for them, e.g. Table.

    class Table:
        ...
        @classmethod
        def _get_create_sql(cls):
            CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS {name} ({fields});"
            ...

New models inherit from the table class and set `Columns` as their class variables.

    class Author(Table):
        name = Column(str)
        age = Column(int)

Columns hold information about the type of the attributes that a certain table, e.g. Author, holds.
It provides methods to translate those types to SQL-types.

    class Column:
        def __init__(self, column_type: type):
            self.type = column_type
    
        @property
        def sql_type(self):
            SQLITE_TYPE_MAP = {
                int: "INTEGER",
                float: "REAL",
                str: "TEXT",
                bytes: "BLOB",
                bool: "INTEGER",  # 0 or 1
            }
            return SQLITE_TYPE_MAP[self.type]

ForeignKeys are similar to Columns but instead of holding holding fundamental types like `int` or `str`, it holds other specific table types, e.g. `Author`

    class ForeignKey:
        def __init__(self, table: type[Table]):
            self._table = table
    
        @property
        def table(self):
            return self._table
    
    # example usage
    class Book(Table):
        title = Column(str)
        published = Column(bool)
        author = ForeignKey(Author)

