from langgraph.checkpoint.memory import MemorySaver


def get_checkpointer() -> MemorySaver:
    """Dev-mode in-memory checkpointer. Swap with PostgresSaver for prod."""
    return MemorySaver()
