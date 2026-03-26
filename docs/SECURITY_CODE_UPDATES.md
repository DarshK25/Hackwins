# Team Security Code Updates

## Overview

This feature stores and validates a shared team security code for protected business actions.

Important distinction:

- Clerk handles user authentication
- `users` documents do not store password hashes
- only `business_organizations.teamActionCodeHash` stores a BCrypt hash, and it is used for team action authorization, not login

## Current Behavior

### Team security code storage

`TeamSecurityCodeService` saves the shared team code to the organization record:

```java
private String teamActionCodeHash;
```

That field lives on the business organization document and remains the source of truth for:

- creating invoices
- creating clients
- other owner-controlled protected team actions

### User records

User records are now Clerk-backed identity records and should not contain:

- `passwordHash`

If older data still has that field, clean it up once with:

```javascript
db.users.updateMany(
  { passwordHash: { $exists: true } },
  { $unset: { passwordHash: "" } }
)
```

## Team Security Update Flow

1. Owner sets or updates the team security code
2. Backend hashes the raw code with BCrypt
3. Hash is stored in `business_organizations.teamActionCodeHash`
4. On updates, active non-owner members are notified by email

## Frontend Access Rules

- owners can manage the team security code
- owners can invite members
- non-owners can view the team list but not the team security management UI

## Validation Checklist

- [ ] Owner can set initial team security code
- [ ] Owner can update existing team security code
- [ ] `business_organizations.teamActionCodeHash` persists after reload
- [ ] Invited or onboarded users do not get a `passwordHash`
- [ ] Members receive email when the team code changes
- [ ] Only owners see team security management controls

## Notes

- There is no user password persistence in this flow
- any older references to "hash password" in user terms should be interpreted as the organization team security code hash
