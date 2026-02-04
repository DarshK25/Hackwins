# Troubleshooting, Tradeoffs, and Git Guide

## 🔧 AI Gateway Problems & Solutions Log

### 1. AI Gateway 500 Error on Client Creation
**Problem:** The seeding script was failing with a 500 Internal Server Error when creating a client.
**Diagnosis:** The Backend Core (Java) was returning a JSON response with a `message` field for errors, but the AI Gateway's `BackendHttpAdapter` was only looking for an `error` field.
**Solution:** Updated `BackendHttpAdapter._request`:
```python
error = response_data.get("error") or response_data.get("message")
```
**Lesson:** Always inspect the *exact* JSON wire format of the upstream service when building adapters.

### 2. Authentication Failure in Agents (BALANCE_CHECK)
**Problem:** The `BALANCE_CHECK` intent was failing because the `FinanceAgent` calls `backend_adapter.get_balance()`, but the backend requires an authenticated user context (JWT) which wasn't being passed.
**Diagnosis:** The `BackendHttpAdapter` method signatures accepted `context`, but `test_agents.py` and `FinanceAgent` weren't extracting/passing the `Authorization` header from the incoming request.
**Solution:**
1.  Updated `test_agents.py` to extract the Bearer token and put it in `context["auth_token"]`.
2.  Updated `BackendHttpAdapter._request` to look for `context["auth_token"]` and set the `Authorization` header.
**Lesson:** Context propagation is critical in microservices. The token must travel from User -> Gateway -> Agent -> Adapter -> Backend.

---

## ☕ Backend Core Development Issues Log
*This section summarizes the technical challenges, bugs, and code review feedback addressed during the development and stabilization of the `feature/backend-core` branch.*

### 1. Compilation & Build Issues

#### 1.1 `PageResponse` Builder Error
*   **Problem:** The `PageResponse` class was missing the `@Builder` annotation, but `AuditLogController` was attempting to use the builder pattern.
*   **Solution:** Added Lombok's `@Builder`, `@NoArgsConstructor`, and `@AllArgsConstructor` to `PageResponse.java`.

#### 1.2 Startup Failure (OAuth2)
*   **Problem:** Application failed to start with `NoSuchBeanDefinitionException` for `ClientRegistrationRepository`. Spring Security's `oauth2Login()` was enabled, but no OAuth2 clients were configured in `application.yml`.
*   **Solution:** Added placeholder Google OAuth2 configuration (`client-id` and `client-secret`) to `application.yml` to satisfy the bean requirement.

#### 1.3 Circular Dependency
*   **Problem:** Runtime startup error due to a circular dependency cycle: `SecurityConfig` -> `OAuth2SuccessHandler` -> `AuthService` -> `PasswordEncoder` -> `SecurityConfig`.
*   **Solution:** Extracted `PasswordEncoder` bean definition into a new, separate configuration class `PasswordEncoderConfig.java` to break the cycle.

### 2. Test Failures (`InvoiceControllerTest`)

#### 2.1 Missing Dependency Injection
*   **Problem:** `UnsatisfiedDependencyException` when loading the application context for `@WebMvcTest`. The test context lacked beans for `JwtFilter`, `JwtProvider`, `UserDetailsService`, `AuthEntryPoint`, and `OAuth2SuccessHandler`.
*   **Solution:** Added `@MockBean` for all missing security-related dependencies in `InvoiceControllerTest.java`.

#### 2.2 Security Configuration & 403 Errors
*   **Problem:** Tests failed with 403 Forbidden or 302 Found (redirect to login) because the mock MVC requests were not authenticated and lacked CSRF tokens.
*   **Solution:**
    1.  Added `spring-security-test` dependency.
    2.  Annotated test class with `@WithMockUser`.
    3.  Added `.with(csrf())` to request builders.
    4.  Correctly mocked `JwtFilter` behavior (eventually restored real filter with mocked dependencies) to ensure the filter chain proceeded correctly.

### 3. CodeRabbit Review Feedback (Security & Quality)

#### 3.1 Unsecured AI Gateway Module [CRITICAL]
*   **Problem:** CodeRabbit flagged an unsecured endpoint. Upon investigation, a rogue `ai-gateway` directory was found at the project root.
*   **Solution:** Deleted the entire `ai-gateway` directory as it was not part of the core backend requirements.

#### 3.2 Plaintext Passwords [CRITICAL]
*   **Problem:** `UserService` was storing passwords directly as plaintext strings.
*   **Solution:** Injected `PasswordEncoder` into `UserService` and updated `hashPassword()` to use `passwordEncoder.encode()`.

#### 3.3 Broken Invite Status Check [BUG]
*   **Problem:** `UserService` compared an Enum (`invite.getStatus()`) with a String literal `"PENDING"`, which always evaluated to `false`.
*   **Solution:** Changed comparison to use the Enum constant: `Invite.InviteStatus.PENDING != invite.getStatus()`.

#### 3.4 Insecure Header Handling (Impersonation Risk) [CRITICAL]
*   **Problem:** `JwtFilter` trusted `X-User-Id` and `X-Org-Id` headers directly from the client without verification, allowing potential impersonation.
*   **Solution:** Added validation logic in `JwtFilter` to ensure the `X-User-Id` header matches the ID extracted from the validated JWT token. Wrapped the context setup in a `try-finally` block to ensure `OrgContext.clear()` is always called.

#### 3.5 Build Artifacts in Version Control
*   **Problem:** `target/` directory files were committed to the repository.
*   **Solution:** Removed `backend/target/` from git validation.

#### 3.6 Spring Boot Version
*   **Problem:** Version 3.2.1 is end-of-life/vulnerable.
*   **Attempt:** Tried upgrading to 3.2.14.
*   **Result:** Upgrade caused `UnresolvableModelException` build failures.

#### 3.7 Repository Enum Mismatch [BUG]
*   **Problem:** `UserService.getPendingInvites` and `createInvite` were passing a String `"PENDING"` to repository methods that query the status column, which is mapped to an Enum. This causes type mismatch errors or invalid queries.
*   **Solution:** Refactored `InviteRepository` methods (`findAllByOrgIdAndStatus`, `existsByEmailAndOrgIdAndStatus`) to accept `Invite.InviteStatus` instead of String. Updated `UserService` to pass `Invite.InviteStatus.PENDING`.

---

## ⚖️ Tradeoffs

### 1. Synchronous HTTP vs. gRPC
**Decision:** We are currently using **HTTP/REST** (httpx) for Gateway-to-Backend communication.
**Tradeoff:** 
*   *Pros:* Easier to debug (readable JSON), standard tooling, familiar to all devs.
*   *Cons:* Higher latency, larger payload size compared to gRPC.
**Future:** We plan to migrate to gRPC for performance in Phase 5/6, but REST allows faster iteration during MVP.

### 2. Lazy Singleton for Backend Adapter
**Decision:** `get_backend_adapter()` uses a global singleton.
**Tradeoff:** 
*   *Pros:* Simplicity, reuses the connection pool (critical for performance).
*   *Cons:* Makes unit testing slightly harder (need to mock the singleton or reset it).
**Mitigation:** Good testing patterns allow for dependency injection overrides if needed.

---

## 🐙 Git Branching & Synchronization Guide

**Current Situation:**
- `feature/backend-core`: Contains the Java Backend MVP.
- `ai-gateway`: Contains the Python AI Gateway MVP.
- `dev` (or `apigateway`): Integration branches.

### The "Missing Folder" Problem
**Symptom:** When switching from `ai-gateway` branch to `feature/backend-core`, the `ai-gateway` folder disappears.
**Cause:** The `ai-gateway` directory is not tracked in the `feature/backend-core` branch. Git cleans up "untracked" files that are tracked in the current branch when you switch.

### Solution: The "Grand Merge"

To synchronize everything so all branches have all folders:

1.  **Go to your integration branch (e.g., `dev` or `main`)**:
    ```bash
    git checkout dev
    ```

2.  **Merge Backend**:
    ```bash
    git merge feature/backend-core
    ```

3.  **Merge AI Gateway**:
    ```bash
    git merge ai-gateway
    ```

4.  **Resolve Conflicts**: If `README.md` or common files conflict, edit them to keep both sections.

5.  **Push Up**:
    ```bash
    git push origin dev
    ```

Now, anyone pulling `dev` will have both `MoneyOps/backend` and `MoneyOps/ai-gateway`.
