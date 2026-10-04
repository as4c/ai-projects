"""
Disinterest Detection for Call Termination
Detects when user shows lack of interest and suggests call termination
"""
from typing import Tuple


class DisinterestDetector:
    """Detects user disinterest and manages disinterest state"""

    def __init__(self):
        self.disinterest_count = 0
        self.negative_keywords = [
            # English
            "not interested", "don't want", "not now", "busy",
            "no time", "can't", "won't", "stop", "end", "hang up",
            "not available", "later", "maybe later",
            # Hindi
            "मत करो", "बंद करो", "रुको", "समय नहीं",
            "बाद में", "इच्छा नहीं", "रुचि नहीं", "काम है", "व्यस्त"
        ]
        self.short_response_threshold = 5  # characters

    def is_disinterested(self, user_response: str) -> bool:
        """
        Check if user response indicates disinterest

        Args:
            user_response: User's speech response

        Returns:
            True if disinterested, False otherwise
        """
        if not user_response:
            return False

        response_lower = user_response.lower().strip()

        # Check for explicit negative keywords
        if any(keyword in response_lower for keyword in self.negative_keywords):
            self.disinterest_count += 1
            print(f"Disinterest detected: keyword match (count: {self.disinterest_count})")
            return True

        # Check for very short responses
        if len(user_response.strip()) < self.short_response_threshold:
            self.disinterest_count += 1
            # If multiple consecutive short responses, consider it disinterest
            if self.disinterest_count >= 2:
                print(f"Disinterest detected: {self.disinterest_count} consecutive short responses")
                return True
        else:
            self.reset_disinterest_count()  # Reset if a meaningful response is given

        return False

    def reset_disinterest_count(self):
        """Reset disinterest counter when a meaningful response is received"""
        self.disinterest_count = 0


def detect_disinterest(response: str, response_length: int = 0) -> Tuple[bool, str]:
    """
    Detect if user shows lack of interest based on their response

    Args:
        response: User's speech response
        response_length: Length of response in characters

    Returns:
        Tuple of (is_disinterested, reason)
    """
    if not response:
        return False, ""

    response_lower = response.lower().strip()

    # Very short responses (less than 3 characters) might indicate disinterest
    if len(response_lower) < 3:
        return True, "Very short response"

    # Negative/disinterest indicators in Hindi and English
    disinterest_keywords = [
        # English
        "not interested", "don't want", "not now", "busy",
        "no time", "can't", "won't", "stop", "end", "hang up",
        "not available", "later", "maybe later",
        # Hindi
        "मत करो", "बंद करो", "रुको", "समय नहीं",
        "बाद में", "इच्छा नहीं", "रुचि नहीं", "काम है", "व्यस्त"
    ]

    # Check for disinterest keywords
    for keyword in disinterest_keywords:
        if keyword in response_lower:
            return True, f"Contains disinterest keyword: {keyword}"

    # Check for very negative responses
    negative_words = [
        "bad", "worst", "terrible", "hate", "dislike", "awful",
        "बुरा", "बहुत बुरा", "नापसंद", "घृणा"
    ]

    negative_count = sum(1 for word in negative_words if word in response_lower)
    if negative_count >= 2:  # Multiple negative words
        return True, "Multiple negative words detected"

    # Check response length - very short might indicate disinterest
    # But only if it's not a simple yes/no answer
    if response_length < 5 and response_lower not in ["yes", "no", "हाँ", "नहीं", "ok", "ठीक"]:
        return True, "Very short non-committal response"

    return False, ""


def should_terminate_call(
    response: str,
    consecutive_short_responses: int = 0,
    negative_responses_count: int = 0
) -> Tuple[bool, str]:
    """
    Determine if call should be terminated based on multiple factors

    Args:
        response: Current user response
        consecutive_short_responses: Number of consecutive very short responses
        negative_responses_count: Number of negative responses so far

    Returns:
        Tuple of (should_terminate, reason)
    """
    is_disinterested, reason = detect_disinterest(response, len(response))

    if is_disinterested:
        return True, reason

    # If multiple consecutive very short responses (less than 5 chars)
    if consecutive_short_responses >= 3:
        return True, "Multiple consecutive very short responses"

    # If multiple negative responses
    if negative_responses_count >= 2:
        return True, "Multiple negative responses"

    return False, ""
