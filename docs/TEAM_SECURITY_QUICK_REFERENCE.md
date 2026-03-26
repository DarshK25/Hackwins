# Quick Reference: Team Security Code

## What Is Stored Where

### `users`

- Clerk identity data only
- no `passwordHash`

### `business_organizations`

- `teamActionCodeHash`
- BCrypt hash of the shared team security code

## Key Rule

The team security code is not a user password. It belongs to the organization and is used only for protected team actions.

## Current Expected Behavior

1. Owner sets or updates the team security code
2. Backend hashes the code
3. Hash is stored in `business_organizations.teamActionCodeHash`
4. Members receive an email when the code changes
5. Non-owners do not see team security management controls

## One-Time Mongo Cleanup

Remove stale user password hashes from existing records:

```javascript
db.users.updateMany(
  { passwordHash: { $exists: true } },
  { $unset: { passwordHash: "" } }
)
```

## Verification

```text
Owner sets team code
  -> organization document contains teamActionCodeHash
  -> user document does not contain passwordHash

Invite accepted
  -> user joins organization
  -> user document does not contain passwordHash
```

## Operational Notes

- Clerk is the authentication system
- backend password-based login/register is disabled
- organization team security hashing remains active
