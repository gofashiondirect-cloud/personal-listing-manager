# JavaScript / TypeScript standard (sources: MDN, TypeScript handbook, OWASP)
- Prefer TypeScript with `strict`; no `any` without a comment saying why.
- `const` by default, `let` when reassigned, never `var`; `===` only.
- Small pure functions; one module = one responsibility; named exports.
- Handle every promise: `await` inside `try/catch` or `.catch()`; show the user a useful error, log the detail.
- Validate all external input (forms, URL params, API responses) at the boundary.
- Never build HTML with string concatenation of user data (`innerHTML`); use `textContent` or framework escaping.
- No secrets or API keys in client code; read config from environment variables on the server.
- Remove `console.log` debugging before committing; no dead code or commented-out blocks.
- Use the platform first (fetch, URL, Intl, structuredClone) before adding a dependency.
