# API standard (sources: HTTP semantics RFC 9110, OWASP API Security Top 10)
- Resource-style URLs (`/orders/{id}`), correct verbs (GET reads, POST creates, PUT/PATCH updates, DELETE removes).
- Correct status codes: 200/201/204, 400 validation, 401 unauthenticated, 403 forbidden, 404 missing, 409 conflict, 422 semantic errors, 500 only for bugs.
- One consistent error shape, e.g. `{"error": {"code": "...", "message": "..."}}`; never leak stack traces.
- Validate and type every input; check authorisation on every request for the specific object (no IDOR).
- Paginate list endpoints; rate-limit public ones.
- Version breaking changes; keep responses backward compatible otherwise.
- Document each endpoint (request, response, errors) where the project keeps API docs.
