# Endpoint contract checklist

Use for each proposed wiki operation. Label unsettled values as proposals;
read ADR-007–009 before specifying access or paths.

- Purpose, method and proposed route; relationship to shared service and OpenAPI.
- Input: authentication, path/query/body schema, validation and size constraints.
- Authorization: guest, reader (including public filtering), editor and admin;
  check direct API requests independently of UI visibility.
- Outputs: success representation and documented status; validation, conflict,
  unauthenticated, forbidden and missing-resource responses as applicable.
- State effects: transaction and idempotence; unchanged path, no cascading
  deletion; avoid disclosing private pages in errors or lists.
- Tests: authorized success, each denied role, invalid input, missing/conflicting
  data and shared-service behavior; run relevant tests once they exist.
- Record outstanding decisions before implementation. Example route names and
  status codes are not commitments until agreed in the stage plan.
