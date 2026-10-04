"""
Generate insights from call transcripts using LLM
Uses factory pattern to support multiple providers
Generates structured, actionable insights with specific observations
"""
from typing import Optional, Dict, Any
from .llm_providers import LLMProviderFactory
from django.conf import settings


# Structured insight prompt template
INSIGHT_PROMPT_TEMPLATE = """You are an expert UX researcher and customer insights analyst. Analyze the following customer call transcript and user data to generate actionable, data-driven insights.

## CALL TRANSCRIPT:
{transcript}

## USER DATA:
- Name: {user_name}
- Gender: {user_gender}
- Age: {user_age}
- Event/Context: {event_name}
- Language: {language}

## USER RESPONSES BY QUESTION:
{user_responses_formatted}

## INSTRUCTIONS:
Generate 5-8 numbered insights that are:
1. **Specific and Actionable** - Each insight should suggest a clear action or improvement
2. **Data-Backed** - Reference specific user statements or patterns from the transcript
3. **Categorized** - Cover different aspects: pain points, preferences, suggestions, sentiment
4. **Quantifiable when possible** - Include specific metrics or comparisons

## REQUIRED FORMAT:
Each insight should be a complete sentence in this style:
1. [Category: Pain Point/Preference/Suggestion/Observation] Brief, actionable insight with specific evidence.

## EXAMPLE INSIGHTS (for reference, generate new ones based on actual transcript):
1. [Pain Point] User expressed frustration with pricing, specifically mentioning "paisa zyada hai" - suggests need for clearer value proposition or flexible pricing tiers.
2. [Preference] User prefers shorter content formats as indicated by "short video better" - consider promoting bite-sized learning modules.
3. [Suggestion] User directly requested better technical support, citing app crashes - prioritize stability fixes in next release.
4. [Observation] Response time was hesitant when discussing competitor apps - may indicate ongoing comparison shopping behavior.
5. [Sentiment] Overall tone shifted from neutral to slightly negative when discussing content quality - content team should review recent additions.

Now analyze the actual transcript and generate insights:"""


def format_user_responses(user_responses: dict) -> str:
    """Format user responses dictionary for the prompt"""
    if not user_responses:
        return "No structured responses available"

    formatted = []
    for question_id, response in user_responses.items():
        formatted.append(f"- {question_id}: \"{response}\"")

    return "\n".join(formatted) if formatted else "No structured responses available"


def generate_call_insights(
    transcript: str,
    user_responses: dict = None,
    provider: str = None,
    user_data: dict = None
) -> Optional[str]:
    """
    Generate structured, actionable insights from call transcript

    Args:
        transcript: Full call transcript
        user_responses: Dictionary of user responses by question ID
        provider: LLM provider name ('openai', 'gemini', 'assemblyai')
        user_data: Dictionary with user info (name, gender, age, event_name, language)

    Returns:
        Formatted insights string or None if generation fails
    """
    if not transcript or len(transcript.strip()) < 50:
        return "Insufficient transcript data for insight generation."

    # Get provider
    provider_name = provider or getattr(settings, 'DEFAULT_LLM_PROVIDER', 'gemini')
    llm_provider = LLMProviderFactory.create_provider(provider_name)

    if not llm_provider:
        print(f"Failed to create LLM provider: {provider_name}")
        return None

    # Extract user data with defaults
    user_data = user_data or {}
    user_name = user_data.get('name', 'Unknown')
    user_gender = user_data.get('gender', 'Unknown')
    user_age = user_data.get('age', 'Unknown')
    event_name = user_data.get('event_name', 'General Survey')
    language = user_data.get('language', 'hi')

    # Format the prompt
    prompt = INSIGHT_PROMPT_TEMPLATE.format(
        transcript=transcript,
        user_name=user_name,
        user_gender=user_gender,
        user_age=user_age,
        event_name=event_name,
        language=language,
        user_responses_formatted=format_user_responses(user_responses)
    )

    try:
        # Generate insights using LLM
        insights = llm_provider.generate_insights(prompt, user_responses)

        if insights:
            # Clean up and format
            insights = insights.strip()

            # Ensure numbered format
            if not insights.startswith('1.') and not insights.startswith('1)'):
                # Try to extract just the insights if there's preamble
                lines = insights.split('\n')
                insight_lines = []
                for line in lines:
                    line = line.strip()
                    if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                        insight_lines.append(line)

                if insight_lines:
                    insights = '\n'.join(insight_lines)

            return insights

        return None

    except Exception as e:
        error_msg = str(e).lower()
        if 'quota' in error_msg or '429' in error_msg:
            print(f"LLM quota exceeded for insight generation")
            return generate_fallback_insights(transcript, user_responses, user_data)
        print(f"Error generating insights: {e}")
        return None


def generate_fallback_insights(
    transcript: str,
    user_responses: dict = None,
    user_data: dict = None
) -> str:
    """
    Generate basic insights without LLM (keyword-based analysis)
    Used when LLM quota is exceeded
    """
    insights = []
    transcript_lower = transcript.lower()

    # Extract user data
    user_data = user_data or {}
    event_name = user_data.get('event_name', 'survey')

    # Pricing analysis
    pricing_keywords = ['price', 'cost', 'paisa', 'mahanga', 'expensive', 'प्राइस', 'पैसा', 'महंगा']
    if any(kw in transcript_lower for kw in pricing_keywords):
        insights.append("1. [Pain Point] User mentioned pricing/cost concerns - consider reviewing pricing strategy or value communication.")

    # Content analysis
    content_keywords = ['content', 'quality', 'boring', 'interesting', 'maza', 'maja', 'मजा']
    if any(kw in transcript_lower for kw in content_keywords):
        insights.append(f"{len(insights)+1}. [Preference] User discussed content quality/preferences - review content strategy based on feedback.")

    # Technical issues
    tech_keywords = ['error', 'bug', 'crash', 'slow', 'problem', 'issue', 'एरर', 'प्रॉब्लम']
    if any(kw in transcript_lower for kw in tech_keywords):
        insights.append(f"{len(insights)+1}. [Pain Point] Technical issues mentioned - prioritize stability and bug fixes.")

    # Usage patterns
    usage_keywords = ['time nahi', 'busy', 'use nahi', 'forgot', 'भूल', 'समय नहीं']
    if any(kw in transcript_lower for kw in usage_keywords):
        insights.append(f"{len(insights)+1}. [Observation] User cited time constraints or low usage - consider engagement improvement features.")

    # Positive sentiment
    positive_keywords = ['good', 'great', 'nice', 'helpful', 'accha', 'अच्छा', 'बढ़िया']
    if any(kw in transcript_lower for kw in positive_keywords):
        insights.append(f"{len(insights)+1}. [Sentiment] Positive feedback detected - identify specific features that resonated.")

    # Negative sentiment
    negative_keywords = ['bad', 'worst', 'hate', 'terrible', 'खराब', 'बुरा']
    if any(kw in transcript_lower for kw in negative_keywords):
        insights.append(f"{len(insights)+1}. [Sentiment] Negative sentiment detected - follow up to understand specific pain points.")

    # User responses analysis
    if user_responses:
        response_count = len(user_responses)
        insights.append(f"{len(insights)+1}. [Observation] User provided {response_count} responses during the call - engagement level: {'High' if response_count > 4 else 'Moderate' if response_count > 2 else 'Low'}.")

    # Event-specific insight
    if 'cancel' in event_name.lower():
        insights.append(f"{len(insights)+1}. [Context] This was a subscription cancellation feedback call - insights are critical for churn reduction.")

    if not insights:
        insights.append("1. [Observation] Call completed but specific patterns could not be identified from keyword analysis. Manual review recommended.")

    return '\n'.join(insights)

