# Secret Management and Rotation

## Policy
- Never commit real provider keys (`GROQ_API_KEY`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, `ASSEMBLYAI_API_KEY`, `CARTESIA_API_KEY`).
- Keep only placeholders in project `.env` files.
- Load secrets from OS/user environment variables or a secret manager.

## Local Setup (PowerShell)
```powershell
setx GROQ_API_KEY "<new_groq_key>"
setx LIVEKIT_URL "wss://<your-livekit>.livekit.cloud"
setx LIVEKIT_API_KEY "<new_livekit_key>"
setx LIVEKIT_API_SECRET "<new_livekit_secret>"
setx ASSEMBLYAI_API_KEY "<new_assemblyai_key>"
setx CARTESIA_API_KEY "<new_cartesia_key>"
```
Open a new terminal after `setx`.

## Immediate Rotation Checklist
1. Revoke all previously exposed keys in provider dashboards.
2. Generate new keys for Groq, LiveKit, AssemblyAI, and Cartesia.
3. Update local environment variables and deployment secrets.
4. Restart `ai-gateway` and `voice-service`.
5. Verify with:
   - `GET /api/v1/test/health-llm`
   - LiveKit worker registration logs in voice-service.

## CI/CD
- Store secrets in deployment environment (GitHub Actions Secrets, cloud secret manager, Kubernetes secrets).
- Do not inject secrets via committed config files.
