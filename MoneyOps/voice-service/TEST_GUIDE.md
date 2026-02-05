# Quick Test Guide - STT Fix Verification

## What Was Fixed

✅ **Enabled AssemblyAI STT** - Agent can now transcribe speech to text  
✅ **Added event logging** - You can see what the user says and agent responds  
✅ **Made API key required** - Prevents running without STT configured  

---

## Run the Agent

```bash
cd "C:\Users\Paarth kothari\OneDrive\Desktop\Projects\Livekit_voice_agent\moneyops\MoneyOps\voice-service"
python -m app.agent.entrypoint dev
```

---

## What to Look For

### ✅ SUCCESS - You'll see these new logs:

```
user_speech_recognized {"text": "your question here", "session_id": "..."}
agent_response {"text": "agent's answer", "session_id": "..."}
```

### ❌ BEFORE (broken) - You only saw:

```
input stream attached
start reading stream
# No user_speech_recognized!
```

---

## Test Phrases

Try speaking these clearly:

1. **"Hello, can you hear me?"**
   - Should see: `user_speech_recognized {"text": "Hello, can you hear me?"}`

2. **"Show me overdue invoices"**
   - Should see: `user_speech_recognized {"text": "Show me overdue invoices"}`
   - Should see: `function_called {"function": "process_financial_request"}`

3. **"What is my outstanding amount?"**
   - Should see: User speech logged
   - Should see: Agent processes and responds

---

## Tips for Best Results

1. **Speak clearly** and pause for 1-2 seconds after speaking
2. **Wait for the agent** to finish responding before speaking again
3. **Check the logs** for `user_speech_recognized` - that's the key indicator
4. **Use a good microphone** - built-in laptop mics work but headset is better

---

## If Something Goes Wrong

### No `user_speech_recognized` logs?

1. Check microphone permissions in browser
2. Verify AssemblyAI API key is valid
3. Check network connection to AssemblyAI

### Agent responds but with wrong answer?

✅ This means STT is working! The issue is now with LLM/AI Gateway, not STT.

### Slow responses?

Normal for first few queries. AssemblyAI needs to warm up.

---

## Next Steps After Testing

Once you confirm STT is working:

1. ✅ Mark verification complete
2. 🎉 Agent is fully functional
3. 🚀 Ready for production use

---

## Quick Verification Checklist

- [ ] Agent starts without errors
- [ ] Connected to LiveKit room
- [ ] Microphone is enabled
- [ ] Spoke a test phrase
- [ ] Saw `user_speech_recognized` in logs
- [ ] Agent responded appropriately
- [ ] Saw `agent_response` in logs

If all checked ✅ - **STT is working!**
