# React standard (sources: react.dev, WCAG 2.2 AA)
- REACT-01 Function components and hooks only; one component per file, named after the file.
- REACT-02 Keep state as low as possible; derive values instead of syncing them with `useEffect`.
- REACT-03 `useEffect` only to sync with external systems; every effect has correct dependencies and cleanup.
- REACT-04 Stable `key`s from data ids, never array indexes for reorderable lists.
- REACT-05 Every data fetch handles loading, empty and error states in the UI.
- REACT-06 Accessibility: semantic elements first, labels on inputs, `alt` on images, keyboard support for custom controls.
- REACT-07 Split big components (~150+ lines) into smaller ones; lift reusable logic into custom hooks.
- REACT-08 Memoise (`useMemo`/`useCallback`/`memo`) only when a measured problem exists.
- REACT-09 Follow the framework's conventions (Next.js app router, server vs client components) for the installed version.
