# UICP Runtime Specification

## Verified Runtime Environment

- Python: 3.12.13
- Platform: Ubuntu / GCC 11.4.0 (Google Colab VM)
- cryptography: 43.0.3
- openai: 2.32.0

## Validation Status

All phase test suites passed against this runtime:

- Phase 1: 26/26
- Phase 2: 14/14
- Phase 3: 21/21
- Phase 4: 43/43
- Phase 5: 30/30
- Binding extraction: 17/17

## Validation Date

May 21, 2026

## Important Note

These correctness guarantees are tied to this exact runtime.
Any dependency update must be followed by a full re-run of
all test suites before the guarantees can be re-asserted.
