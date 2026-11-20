# DreamQt Clean-Room Development Rules

## 1. Project Objective

Develop an independently implemented Python binding framework
for Qt 6 with PyQt6-compatible public APIs and behavior.

The implementation must not depend on PyQt6 implementation code.

## 2. Permitted Reference Material

- Official Qt C++ documentation.
- Public Qt C++ headers, subject to their licenses.
- Publicly available API documentation.
- Independently authored functional specifications.
- Approved black-box compatibility observations.
- Independently authored test cases.

## 3. Prohibited Material

- PyQt6 upstream implementation source code.
- PyQt6 source distributions used as implementation templates.
- Existing PyQt6 SIP specification files.
- Generated PyQt6 wrapper source code.
- Decompiler or disassembler output intended to reconstruct
  PyQt6 implementation code.
- Copied PyQt6 implementation fragments.
- Unverified third-party implementations.

## 4. Team Separation

The specification team is responsible for establishing
the required public API and observable behavior.

The implementation team is responsible for developing
DreamQt independently.

The implementation team receives only approved specifications,
test contracts, public Qt interfaces, and permitted references.

## 5. Provenance

Every third-party dependency and external reference must
be recorded in SOURCE_REGISTER.md.

Uncertain material must be quarantined until reviewed.

## 6. Implementation Requirements

- No undocumented removal of APIs.
- No silent compatibility compromises.
- No unapproved dependencies.
- No copied implementation code.
- Every module must have automated tests.
- Every compatibility failure must be documented.

## 7. Change Control

No implementation may be declared complete without
passing its required compatibility tests.

All architectural decisions must be documented.

## 8. Licensing

Every dependency must undergo an individual license audit.

DreamQt must not assume that licensing permissions
for Qt automatically extend to third-party components.