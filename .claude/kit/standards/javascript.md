# JavaScript / TypeScript standard (sources: MDN, TypeScript handbook, OWASP)
- JS-01 Prefer TypeScript with `strict`; no `any` without a comment saying why.
- JS-02 `const` by default, `let` when reassigned, never `var`; `===` only.
- JS-03 Small pure functions; one module = one responsibility; named exports.
- JS-04 Handle every promise: `await` inside `try/catch` or `.catch()`; show the user a useful error, log the detail.
- JS-05 Validate all external input (forms, URL params, API responses) at the boundary.
- JS-06 Never build HTML with string concatenation of user data (`innerHTML`); use `textContent` or framework escaping.
- JS-07 No secrets or API keys in client code; read config from environment variables on the server.
- JS-08 Remove `console.log` debugging before committing; no dead code or commented-out blocks.
- JS-09 Use the platform first (fetch, URL, Intl, structuredClone) before adding a dependency.
