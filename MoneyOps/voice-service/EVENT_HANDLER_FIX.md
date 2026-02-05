# Event Handler Fix - Quick Note

## The Error

```
ValueError: Cannot register an async callback with `.on()`. 
Use `asyncio.create_task` within your synchronous callback instead.
```

## The Fix

Changed event handlers from **async** to **sync**:

```diff
-@session.on("user_speech_committed")
-async def on_user_speech(msg):
+@session.on("user_speech_committed")
+def on_user_speech(msg):
```

## Why?

LiveKit's `.on()` event emitter requires **synchronous callbacks**, not async functions.

The logging operations (`logger.info()`) are synchronous anyway, so this is the correct approach.

## Status

✅ **Fixed** - Agent should now start successfully  
✅ **Auto-reload** - Dev mode will restart the agent automatically  
✅ **Ready to test** - Try speaking again once agent reconnects
