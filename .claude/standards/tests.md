# Test standard
- Test behaviour, not implementation: inputs and visible outputs.
- One clear reason to fail per test; descriptive names (`test_total_ignores_cancelled_orders`).
- Cover the normal case, edge cases (empty, zero, large, invalid) and the error path.
- No real network, time or randomness: fake or freeze them.
- Tests are fast and independent; they can run in any order.
- A bug fix comes with a test that fails before the fix.
