# Architecture Convergence Plan (Hard Cut-Over)

## Goal
Converge the backend to the new domain architecture and remove legacy authorization/state assumptions.

## Legacy Assumptions Identified
- `global_role` still present and referenced in model/admin/docs/tests.
- user state still duplicated (`account_status` + `is_active` + `is_archived`).
- academic year state still duplicated (`is_active` + `is_archived`).
- subject state still duplicated (`status` + `is_archived`).
- sprint docs still describe a hybrid transitional architecture.

## Convergence Strategy
1. Identity and access hard cut-over
   - keep `business_identity` as business identity source.
   - make `PlatformAccessGrant` the only platform privilege source.
   - remove runtime dependency on `global_role`.
2. State normalization hard cut-over
   - `User`: make `account_status` authoritative and remove legacy booleans.
   - `AcademicYear`: introduce `status` enum (`ACTIVE`, `CLOSED`, `ARCHIVED`) and remove booleans.
   - `Subject`: keep `status` authoritative and remove `is_archived`.
3. API and validation updates
   - update serializers/views/admin to use normalized enums only.
   - keep login by matricule/email and JWT.
4. Cleanup
   - remove dead compatibility branches and stale transitional comments.
   - update tests to reflect final architecture.
5. Documentation
   - rewrite technical dossier to describe post-convergence architecture only.

## Migration Plan
1. Add new canonical fields if needed (AcademicYear.status), backfill from old fields.
2. Update code to use canonical fields only.
3. Remove deprecated fields (`User.global_role`, `User.is_active`, `User.is_archived`, `AcademicYear.is_active`, `AcademicYear.is_archived`, `Subject.is_archived`).
4. Run checks and full test suite.
