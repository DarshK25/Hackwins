# Implementation Complete

## Summary

MoneyOps now treats Clerk as the only authentication system for users.

- `users` documents no longer need or store `passwordHash`
- team security codes remain stored only as `business_organizations.teamActionCodeHash`
- invite acceptance and onboarding continue to work without any user password persistence

## What Changed

### User authentication data

- Removed remaining backend reads and writes for `users.passwordHash`
- Invite acceptance no longer requires a password
- New users created during onboarding or OAuth bootstrap are saved without a password field
- Legacy password-based backend auth endpoints are disabled and now return a clear Clerk-only error

### Team security code

- Team security code behavior is unchanged
- The only stored hash for this feature is `business_organizations.teamActionCodeHash`
- This hash is still used for protected team actions such as invoice and client creation

### One-time database cleanup

Run this once in MongoDB to remove stale password hashes from existing user documents:

```javascript
db.users.updateMany(
  { passwordHash: { $exists: true } },
  { $unset: { passwordHash: "" } }
)
```

## Validation Checklist

```text
1. Accept an invite without sending a password
2. Confirm the created/updated user document has no passwordHash field
3. Create a new business and confirm the owner user has no passwordHash field
4. Verify business_organizations.teamActionCodeHash is still populated when a team code is set
5. Call /api/auth/login and /api/auth/register and confirm they return the Clerk-only error message
```

## Current Data Model

### `users`

User documents should contain identity and workspace fields such as:

- `id`
- `clerkId`
- `email`
- `name`
- `phone`
- `orgId`
- `role`
- `status`

They should not contain:

- `passwordHash`

### `business_organizations`

Organization documents still contain:

- `teamActionCodeHash`

This field stores the BCrypt hash of the shared team security code. It is not a user login password.
