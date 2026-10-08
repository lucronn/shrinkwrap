"""
Fast deterministic token estimation engine for ShrinkWrap.
"""

def estimate_tokens(text: str) -> int:
    """
    Estimates token count for a text string using standard ~4 char per token heuristic
    with adjustment for code/JSON whitespace and punctuation density.
    """
    if not text:
        return 0
    words = text.split()
    word_count = len(words)
    char_count = len(text)
    
    # Base estimate combining character density and word boundaries
    est = int((char_count / 3.8 + word_count / 0.75) / 2)
    return max(1, est)
