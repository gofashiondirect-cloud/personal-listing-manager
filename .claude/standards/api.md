# API standard (sources: HTTP semantics RFC 9110, OWASP API Security Top 10)
- API-01 Resource-style URLs (`/orders/{id}`), correct verbs (GET reads, POST creates, PUT/PATCH updates, DELETE removes).
- API-02 Correct status codes: 200/201/204, 400 validation, 401 unauthenticated, 403 forbidden, 404 missing, 409 conflict, 422 semantic errors, 500 only for bugs.
- API-03 One consistent error shape, e.g. `{"error": {"code": "...", "message": "..."}}`; never leak stack traces.
- API-04 Validate and type every input; check authorisation on every request for the specific object (no IDOR).
- API-05 Paginate list endpoints; rate-limit public ones.
- API-06 Version breaking changes; keep responses backward compatible otherwise.
- API-07 Document each endpoint (request, response, errors) where the project keeps API docs.
