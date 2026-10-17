"""The AI layer: an "Ask" chat over the client's data, and proactive insights.

Rules it follows (see docs/playbook-v0.md, Phase 5):
- One API key, one monthly cap and one usage log per feature.
- It reads data only through the same metric functions the pages use (so its
  figures match the screens), or read-only SQL through the ai_reader login.
- It never writes data and never sends anything; people act on what it says.
- Record contents (deal names, memos) are data, never instructions.
"""
