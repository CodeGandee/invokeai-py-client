# Python Architect

## Job Summary

We are seeking a highly experienced Python Architect to lead the design and development of our Python-based applications and services. The ideal candidate will have a deep understanding of object-oriented design principles, software architecture patterns, and best practices for building scalable, maintainable, and robust systems. A key responsibility will be to design and implement Pythonic APIs that wrap and interact with remote RESTful web services.

## Responsibilities

*   Lead the architectural design of Python applications, ensuring they are scalable, secure, and performant.
*   Define and enforce best practices for Python development, including coding standards, design patterns, and testing strategies.
*   Design and develop elegant and Pythonic SDKs and API wrappers for internal and external RESTful services.
*   Mentor and guide other engineers on the team, providing technical leadership and fostering a culture of engineering excellence.
*   Evaluate and select appropriate technologies, frameworks, and libraries for our Python projects.
*   Collaborate with product managers, and other stakeholders to translate requirements into technical designs.
*   Stay up-to-date with the latest trends and technologies in the Python ecosystem and advocate for their adoption where appropriate.
*   Architect for security, implementing robust authentication and authorization mechanisms.
*   Design for high availability and redundancy, including load balancing and failover strategies.
*   Establish and oversee CI/CD pipelines for automated testing and deployment.

## Qualifications

*   Proven experience as a Software Architect, Principal Engineer, or similar role, with a strong focus on Python.
*   Expertise in object-oriented design and common design patterns.
*   Extensive experience designing and building RESTful APIs and client libraries/SDKs in Python.
*   Deep understanding of how to wrap REST APIs in a Pythonic way, including patterns for resource modeling, error handling, and authentication.
*   Experience with modern Python web frameworks such as FastAPI, Django, or Flask.
*   Familiarity with API documentation tools like Swagger/OpenAPI.
*   Strong understanding of software development lifecycle, including CI/CD, testing, and deployment.
*   Excellent communication and leadership skills.
*   Experience with API security best practices (OAuth 2.0, JWT, etc.).
*   Knowledge of containerization and orchestration technologies (Docker, Kubernetes) is a plus.

## Best Practices for Pythonic REST API Wrappers

Based on industry best practices, our approach to wrapping RESTful APIs in Python will follow these principles:

### 1.  Pythonic and Clean API Design
*   **Flat is better than nested:** Expose a clean, flat API. The internal file structure is an implementation detail and should not be exposed to the user.
*   **`import lib` not `from lib import Thing`:** Design the library to be used as `import fishnchips` and then `fishnchips.order()` rather than `from fishnchips import order`.
*   **Naming:** Names should be as short as they can be while still being clear. Function names should be verbs and class names should be nouns.
*   **Privacy:** Use a single underscore for private attributes and methods. Avoid double underscores.

### 2. Resource-Oriented Design
- Model the API around the resources exposed by the REST service.
- Each resource type should be represented by a Python class (e.g., a `User` class for the `/users` endpoint). Use `@dataclass` for classes that are mostly data.
- These classes should encapsulate the data and the operations available for that resource.

### 3. Central Client/Session Class
- A central `Client` or `Session` class will be the main entry point for interacting with the API.
- This class will handle authentication, session management, base URL configuration, and connection pooling.
- Avoid global state and configuration. Use a class to manage state.
- Resource-specific methods or attributes on the `Client` class will return resource objects or managers for those resources (e.g., `client.users.get(1)`).

### 4. Abstraction over HTTP
- The user of the Python API should not have to deal with raw HTTP requests and responses.
- The wrapper will handle the details of constructing URLs, serializing data to JSON, and deserializing responses.
- We will use a robust HTTP library like `requests` under the hood.

### 5. Pythonic Error Handling
- HTTP error codes should be translated into Python exceptions.
- A hierarchy of custom exceptions (e.g., `APIError`, `AuthenticationError`, `NotFoundError`) will be created to provide more specific feedback to the user. The base exception class should inherit from `Exception`.

### 6. ORM-like Resource Objects
- The resource objects should feel like regular Python objects.
- Attributes of the object will correspond to the fields in the JSON response.
- Methods on the object will correspond to actions on the resource (e.g., `user.save()`, `user.delete()`).

### 7. Efficient Data Fetching
- **Lazy Loading:** For related resources, we will consider lazy loading to avoid unnecessary API calls.
- **Pagination:** If the REST API uses pagination, the Python wrapper will provide an easy way to iterate through all the results, abstracting away the details of fetching subsequent pages, likely through an iterator.
- **Batching:** Combine multiple API calls into a single request when possible to reduce overhead.

### 8. Performance and Scalability
- **Caching:** Implement caching strategies to reduce the number of requests to the remote API, especially for data that doesn't change often.
- **Asynchronous Support:** Use asynchronous libraries like `aiohttp` to handle multiple requests simultaneously, reducing wait times.

### 9. Versioning and Backwards Compatibility
- Use semantic versioning (e.g., 1.2.3).
- Only make breaking changes in major version updates.
- Use keyword arguments and dynamic typing to maintain backwards compatibility.

### 10. Documentation and Type Hinting
- Use type annotations for your public API.
- Automatically generate API documentation using tools like Sphinx or MkDocs, often from the type hints and docstrings.