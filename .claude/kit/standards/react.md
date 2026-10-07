# React standard (sources: react.dev, WCAG 2.2 AA)
- Function components and hooks only; one component per file, named after the file.
- Keep state as low as possible; derive values instead of syncing them with `useEffect`.
- `useEffect` only to sync with external systems; every effect has correct dependencies and cleanup.
- Stable `key`s from data ids, never array indexes for reorderable lists.
- Every data fetch handles loading, empty and error states in the UI.
- Accessibility: semantic elements first, labels on inputs, `alt` on images, keyboard support for custom controls.
- Split big components (~150+ lines) into smaller ones; lift reusable logic into custom hooks.
- Memoise (`useMemo`/`useCallback`/`memo`) only when a measured problem exists.
- Follow the framework's conventions (Next.js app router, server vs client components) for the installed version.
