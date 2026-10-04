"""
Response Analyzer for Decision Tree Routing
Uses keyword matching for speed, LLM only as fallback for ambiguous cases
OPTIMIZED: Keyword-first approach to minimize latency
"""
from typing import Dict, Optional
import time
from django.conf import settings
from .llm_providers import LLMProviderFactory


# Global cache to track API quota status - avoids repeated failed calls
_quota_exceeded_cache = {
    'gemini': {'exceeded': False, 'last_check': 0},
    'openai': {'exceeded': False, 'last_check': 0},
    'assemblyai': {'exceeded': False, 'last_check': 0},
}
QUOTA_RETRY_INTERVAL = 300  # Retry after 5 minutes


class ResponseAnalyzer:
    """
    Analyze user responses to determine decision tree pathway
    OPTIMIZED: Uses keyword matching primarily, LLM only for truly ambiguous cases
    """

    # Intent keywords mapping for subscription_cancelled
    # Includes both Hindi and English keywords - EXPANDED for better coverage
    INTENT_KEYWORDS = {
        "pricing": [
            # English
            "cost", "price", "expensive", "afford", "budget", "cheap", "money",
            "subscription", "charge", "fee", "amount", "worth", "value",
            # Hindi/Hinglish
            "paisa", "mahanga", "paisa zyada", "paisa nahi", "zyada paisa", "sasta",
            "paise", "kharcha", "rupee", "rupay", "rupaya", "price",
            # Devanagari (Hindi script)
            "महंगा", "पैसा", "पैसे", "खर्चा", "कीमत", "दाम", "रुपया", "रुपये",
            "प्राइस", "कॉस्ट", "महँगा", "मंहगा",  # Added: Hindi transliterations
            # Common phrases
            "too much", "not affordable", "costly", "overpriced", "pricing"
        ],
        "content": [
            # English
            "content", "courses", "topics", "quality", "material", "syllabus",
            "curriculum", "interesting", "enjoy", "boring", "relevant",
            "video", "videos", "lecture", "class", "teacher", "teaching",
            # Hindi/Hinglish
            "maza", "maja", "maza nahi", "maja nahi", "accha nahi", "pasand nahi",
            "course", "lesson", "learning", "study", "padhai",
            # Devanagari
            "मजा", "मज़ा", "पसंद", "अच्छा नहीं", "बोरिंग", "इंटरेस्टिंग नहीं",
            "पढ़ाई", "कोर्स", "विषय", "टॉपिक"
        ],
        "lack_of_use": [
            # English
            "not using", "didn't use", "no time", "busy", "forgot",
            # Hindi/Hinglish
            "use nahi", "time nahi", "engaging nahi", "regular use nahi",
            "use kiya nahi", "time mila nahi", "samay nahi", "bhul gaya",
            "dekha nahi", "open nahi kiya", "istemaal nahi",
            # Devanagari
            "इस्तेमाल", "टाइम", "समय", "व्यस्त", "बिजी", "भूल गया"
        ],
        "technical": [
            # English
            "technical", "bug", "error", "issue", "problem", "glitch",
            "crash", "slow", "not working", "broken", "fix",
            "load", "loading", "hang", "stuck", "freeze", "network", "app",
            # Hindi/Hinglish
            "problem", "issue", "error", "crash", "slow", "hang",
            # Devanagari
            "एरर", "प्रॉब्लम", "इश्यू", "स्लो", "क्रैश", "हैंग"
        ],
        "clarification": [
            # English
            "just", "nothing", "no reason", "don't know", "not sure",
            # Hindi/Hinglish
            "samajh nahi", "bas zarurat nahi", "bas", "kuch nahi",
            "aise hi", "bas aise", "pata nahi", "koi reason nahi",
            # Devanagari
            "बस", "ऐसे ही", "कुछ नहीं", "बस ऐसे", "पता नहीं"
        ]
    }

    def __init__(self, provider: str = None, skip_llm: bool = False):
        """
        Initialize analyzer

        Args:
            provider: LLM provider name
            skip_llm: If True, never use LLM (fastest mode)
        """
        self.provider_name = provider or getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini')
        self.skip_llm = skip_llm
        self.llm_provider = None  # Lazy load only when needed

    def _get_llm_provider(self):
        """Lazy load LLM provider only when actually needed"""
        if self.llm_provider is None:
            self.llm_provider = LLMProviderFactory.create_provider(self.provider_name)
        return self.llm_provider

    def _is_quota_exceeded(self) -> bool:
        """Check if API quota is exceeded (with caching)"""
        cache = _quota_exceeded_cache.get(self.provider_name, {})
        if cache.get('exceeded', False):
            # Check if we should retry
            if time.time() - cache.get('last_check', 0) < QUOTA_RETRY_INTERVAL:
                return True
        return False

    def _mark_quota_exceeded(self):
        """Mark API quota as exceeded"""
        _quota_exceeded_cache[self.provider_name] = {
            'exceeded': True,
            'last_check': time.time()
        }

    def analyze_response(self, response: str, current_question_id: str = "Q1") -> Dict:
        """
        Analyze user response to determine next pathway
        OPTIMIZED: Keyword-first, LLM only when truly needed

        Args:
            response: User's speech input
            current_question_id: Current question ID (e.g., "Q1")

        Returns:
            {
                "pathway": "pricing" | "content" | "lack_of_use" | "technical" | "clarification",
                "confidence": 0.0-1.0,
                "keywords": ["cost", "price"],
                "needs_clarification": False,
                "next_question_id": "Q2a"
            }
        """
        if not response or not response.strip():
            return {
                "pathway": "clarification",
                "confidence": 0.5,
                "keywords": [],
                "needs_clarification": True,
                "next_question_id": "q1a"
            }

        # First, try keyword-based matching (INSTANT - no API call)
        keyword_result = self._analyze_by_keywords(response)

        # OPTIMIZATION: Accept keyword match with confidence >= 0.3 (lowered from 0.7)
        # This covers most cases without needing LLM
        if keyword_result["confidence"] >= 0.3:
            print(f"✅ FAST: Keyword match found: {keyword_result['pathway']} (conf: {keyword_result['confidence']:.2f})")
            return keyword_result

        # OPTIMIZATION: Skip LLM if explicitly disabled or quota exceeded
        if self.skip_llm or self._is_quota_exceeded():
            print(f"⚡ SKIPPING LLM (skip_llm={self.skip_llm}, quota_exceeded={self._is_quota_exceeded()})")
            return keyword_result

        # Only use LLM for truly ambiguous responses
        print(f"🔍 Using LLM for ambiguous response: '{response[:50]}...'")
        llm_result = self._analyze_with_llm(response, current_question_id)

        # Combine results (prefer LLM if confidence is higher)
        if llm_result["confidence"] > keyword_result["confidence"]:
            return llm_result
        else:
            return keyword_result

    def _analyze_by_keywords(self, response: str) -> Dict:
        """
        Analyze response using keyword matching
        OPTIMIZED: More aggressive matching, higher confidence for single strong matches
        """
        response_lower = response.lower()
        # Also check original (for Hindi Devanagari)
        response_original = response

        pathway_scores = {}
        matched_keywords = {}

        # Score each pathway based on keyword matches
        for pathway, keywords in self.INTENT_KEYWORDS.items():
            score = 0
            matched = []
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Check both lowercase and original (for Devanagari)
                if keyword_lower in response_lower or keyword in response_original:
                    # Give higher weight to longer keywords (more specific)
                    weight = 1.0 if len(keyword) < 5 else 1.5 if len(keyword) < 10 else 2.0
                    score += weight
                    matched.append(keyword)

            if score > 0:
                pathway_scores[pathway] = score
                matched_keywords[pathway] = matched

        if not pathway_scores:
            # No keywords matched, likely vague
            return {
                "pathway": "clarification",
                "confidence": 0.3,  # Lower confidence for no match
                "keywords": [],
                "needs_clarification": True,
                "next_question_id": "q1a"
            }

        # Get pathway with highest score
        best_pathway = max(pathway_scores.items(), key=lambda x: x[1])[0]
        max_score = pathway_scores[best_pathway]

        # OPTIMIZED: Higher confidence for any match
        # Single strong keyword match should be enough
        if max_score >= 2.0:
            confidence = 0.9  # Strong match
        elif max_score >= 1.5:
            confidence = 0.7  # Good match
        elif max_score >= 1.0:
            confidence = 0.5  # Weak match
        else:
            confidence = 0.3  # Very weak

        # Map pathway to question ID (use lowercase for consistency)
        pathway_to_question = {
            "pricing": "q2a",
            "content": "q2b",
            "lack_of_use": "q2c",
            "technical": "q2d",
            "clarification": "q1a"
        }

        return {
            "pathway": best_pathway,
            "confidence": confidence,
            "keywords": matched_keywords.get(best_pathway, []),
            "needs_clarification": best_pathway == "clarification",
            "next_question_id": pathway_to_question.get(best_pathway, "q1a")
        }

    def _analyze_with_llm(self, response: str, current_question_id: str) -> Dict:
        """
        Analyze response using LLM for deeper understanding
        OPTIMIZED: Includes quota caching to avoid repeated failed calls
        """
        import json
        import re

        try:
            prompt = f"""Analyze this user response from a subscription cancellation interview and determine the main reason for cancellation.

User Response: "{response}"

Current Question: {current_question_id}

Classify the response into one of these categories:
1. pricing - User mentions cost, price, affordability, budget issues
2. content - User mentions content quality, course relevance, topics, material
3. lack_of_use - User mentions not using the app, lack of time, not engaging, boring
4. technical - User mentions technical issues, bugs, errors, app problems
5. clarification - Response is vague, unclear, or doesn't specify a reason

Respond in JSON format:
{{
    "pathway": "pricing|content|lack_of_use|technical|clarification",
    "confidence": 0.0-1.0,
    "keywords": ["keyword1", "keyword2"],
    "reasoning": "brief explanation"
}}

Respond ONLY with valid JSON, no other text."""

            try:
                llm_provider = self._get_llm_provider()
                analysis_text = llm_provider.generate_insights(prompt, {})
            except Exception as e:
                error_msg = str(e).lower()
                # Mark quota as exceeded for future calls
                if '429' in str(e) or 'quota' in error_msg or 'rate' in error_msg:
                    self._mark_quota_exceeded()
                    print(f"⚠️ Quota exceeded, caching for {QUOTA_RETRY_INTERVAL}s")
                print(f"LLM analysis failed, using keyword fallback: {e}")
                return self._analyze_by_keywords(response)

            if not analysis_text:
                return self._analyze_by_keywords(response)

            # Extract JSON from response (handle markdown code blocks)
            json_match = re.search(r'\{[^{}]*\}', analysis_text, re.DOTALL)
            if json_match:
                try:
                    analysis = json.loads(json_match.group(0))

                    # Map pathway to question ID (use lowercase for consistency)
                    pathway_to_question = {
                        "pricing": "q2a",
                        "content": "q2b",
                        "lack_of_use": "q2c",
                        "technical": "q2d",
                        "clarification": "q1a"
                    }

                    pathway = analysis.get("pathway", "clarification")
                    confidence = float(analysis.get("confidence", 0.5))
                    keywords = analysis.get("keywords", [])

                    return {
                        "pathway": pathway,
                        "confidence": confidence,
                        "keywords": keywords if isinstance(keywords, list) else [],
                        "needs_clarification": pathway == "clarification",
                        "next_question_id": pathway_to_question.get(pathway, "q1a")
                    }
                except json.JSONDecodeError:
                    pass

            return self._analyze_by_keywords(response)

        except Exception as e:
            error_msg = str(e).lower()
            if '429' in str(e) or 'quota' in error_msg or 'rate' in error_msg:
                self._mark_quota_exceeded()
            print(f"LLM analysis failed: {e}")
            return self._analyze_by_keywords(response)

