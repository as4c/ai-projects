"""
Questionnaire Handler for GyanTV User Connect Survey
Manages the conversation flow through the structured questionnaire
"""
from typing import Dict, Optional, List, Tuple
from enum import Enum
import os
from pathlib import Path


class QuestionnaireSection(Enum):
    """Questionnaire sections"""
    INTRODUCTION = "introduction"
    CONTENT_CONSUMPTION = "content_consumption"
    CONTENT_PREFERENCE = "content_preference"
    DEMOGRAPHY = "demography"
    MOTIVATION = "motivation"
    USER_EXPERIENCE = "user_experience"
    COMPETITOR = "competitor"
    SUGGESTIONS = "suggestions"
    COMPLETED = "completed"


class QuestionnaireHandler:
    """
    Handles the GyanTV questionnaire flow
    """

    def __init__(self, user_name: str = None, user_gender: str = None, user_age: str = None, event_name: str = None, language: str = None):
        self.current_section = QuestionnaireSection.INTRODUCTION
        self.current_question_index = 0
        self.responses: Dict[str, str] = {}
        self.introduction_completed = False
        # Track conversation history for transcript formatting
        self.conversation_history: List[Tuple[str, str]] = []  # List of (speaker, text) tuples
        # Track disinterest indicators
        self.consecutive_short_responses = 0
        self.negative_responses_count = 0
        self.should_terminate = False
        # Track total questions asked (limit to 5)
        self.total_questions_asked = 0
        self.MAX_QUESTIONS = 5
        # User data for personalization
        self.user_name = user_name
        self.user_gender = user_gender
        self.user_age = user_age
        self.event_name = event_name  # Questionnaire type/event name
        self.language = language or 'hi'  # Language code (e.g., 'hi', 'en', 'hinglish')

        # Load questionnaire from file if event_name is provided
        self.questions_from_file: List[str] = []
        self.use_file_questions = False
        if event_name:
            self._load_questionnaire_from_file()

    def _load_questionnaire_from_file(self):
        """Load questionnaire questions from file based on event_name and language"""
        try:
            # Get the base directory (ai_researcher folder)
            base_dir = Path(__file__).parent.parent.parent
            questionnaire_dir = base_dir / "questionnaires" / self.event_name

            # Try to load the language-specific file
            lang_file = questionnaire_dir / f"{self.language}.txt"

            if not lang_file.exists():
                # Fallback to English if language file doesn't exist
                lang_file = questionnaire_dir / "en.txt"

            if lang_file.exists():
                with open(lang_file, 'r', encoding='utf-8') as f:
                    content = f.read()

                # Parse questions from the file
                # Questions are typically separated by newlines or bullet points
                lines = content.split('\n')
                questions = []

                for line in lines:
                    line = line.strip()
                    # Skip empty lines, headers, and bullet points
                    if not line or line.startswith('#') or line.startswith('●') or line.startswith('○') or line.startswith('*'):
                        continue
                    # Skip section headers (all caps or title case)
                    if line.isupper() or (len(line) < 50 and not '?' in line and not '?' in line):
                        # Check if it's a question (contains question mark or common question words)
                        if '?' in line or any(word in line.lower() for word in ['what', 'how', 'when', 'where', 'why', 'who', 'क्या', 'कैसे', 'कब', 'कहाँ']):
                            questions.append(line)
                    elif '?' in line or any(word in line.lower() for word in ['what', 'how', 'when', 'where', 'why', 'who', 'क्या', 'कैसे', 'कब', 'कहाँ']):
                        questions.append(line)

                # If we found questions, use them
                if questions:
                    self.questions_from_file = questions[:self.MAX_QUESTIONS]  # Limit to MAX_QUESTIONS
                    self.use_file_questions = True
                    print(f"Loaded {len(self.questions_from_file)} questions from file: {lang_file}")
                else:
                    print(f"No questions found in file: {lang_file}, using default questions")
            else:
                print(f"Questionnaire file not found: {lang_file}, using default questions")
        except Exception as e:
            print(f"Error loading questionnaire from file: {e}, using default questions")

    def get_next_question(self) -> Optional[Tuple[str, str]]:
        """
        Get the next question in the questionnaire
        Limited to MAX_QUESTIONS (5) total questions

        Returns:
            Tuple of (question_text, question_key) or None if completed
        """
        # Check if we've reached the maximum number of questions
        if self.total_questions_asked >= self.MAX_QUESTIONS:
            self.current_section = QuestionnaireSection.COMPLETED
            return None

        # If using questions from file, use those instead
        if self.use_file_questions and self.questions_from_file:
            if not self.introduction_completed:
                # First question is the introduction
                question = self._get_introduction_question()
                if question:
                    self.total_questions_asked += 1
                return question

            # Get next question from file
            if self.current_question_index < len(self.questions_from_file):
                question_text = self.questions_from_file[self.current_question_index]
                question_key = f"question_{self.current_question_index + 1}"
                self.current_question_index += 1
                self.total_questions_asked += 1
                return (question_text, question_key)
            else:
                self.current_section = QuestionnaireSection.COMPLETED
                return None

        # Default behavior: use hardcoded questions
        if not self.introduction_completed:
            question = self._get_introduction_question()
            if question:
                self.total_questions_asked += 1
            return question

        # Route to appropriate section based on current state
        if self.current_section == QuestionnaireSection.INTRODUCTION:
            self.current_section = QuestionnaireSection.CONTENT_CONSUMPTION
            self.current_question_index = 0

        if self.current_section == QuestionnaireSection.CONTENT_CONSUMPTION:
            question = self._get_content_consumption_question()
            if question:
                self.total_questions_asked += 1
                return question
            self.current_section = QuestionnaireSection.CONTENT_PREFERENCE
            self.current_question_index = 0

        if self.current_section == QuestionnaireSection.CONTENT_PREFERENCE:
            question = self._get_content_preference_question()
            if question:
                self.total_questions_asked += 1
                return question
            self.current_section = QuestionnaireSection.DEMOGRAPHY
            self.current_question_index = 0

        if self.current_section == QuestionnaireSection.DEMOGRAPHY:
            question = self._get_demography_question()
            if question:
                self.total_questions_asked += 1
                return question
            self.current_section = QuestionnaireSection.MOTIVATION
            self.current_question_index = 0

        if self.current_section == QuestionnaireSection.MOTIVATION:
            question = self._get_motivation_question()
            if question:
                self.total_questions_asked += 1
                return question
            self.current_section = QuestionnaireSection.USER_EXPERIENCE
            self.current_question_index = 0

        if self.current_section == QuestionnaireSection.USER_EXPERIENCE:
            question = self._get_user_experience_question()
            if question:
                self.total_questions_asked += 1
                return question
            self.current_section = QuestionnaireSection.COMPETITOR
            self.current_question_index = 0

        if self.current_section == QuestionnaireSection.COMPETITOR:
            question = self._get_competitor_question()
            if question:
                self.total_questions_asked += 1
                return question
            self.current_section = QuestionnaireSection.SUGGESTIONS
            self.current_question_index = 0

        if self.current_section == QuestionnaireSection.SUGGESTIONS:
            question = self._get_suggestions_question()
            if question:
                self.total_questions_asked += 1
                return question
            self.current_section = QuestionnaireSection.COMPLETED
            return None

        return None

    def _get_introduction_question(self) -> Tuple[str, str]:
        """Get the introduction question with personalization"""
        # Use user's name if available
        if self.user_name:
            # Determine appropriate title based on gender
            if self.user_gender and self.user_gender.lower() in ['female', 'f', 'woman', 'lady']:
                title = "Madam"
            elif self.user_gender and self.user_gender.lower() in ['male', 'm', 'man', 'sir']:
                title = "Sir"
            else:
                title = "Sir/Madam"

            greeting = f"Hello {self.user_name} {title}! Namaste!"
        else:
            greeting = "Hello! Namaste!"

        return (
            f"{greeting} Main aapke GyanTV app ke experience ke baare mein jaanna chahta hoon. "
            "Hum aapse 2 se 3 minutes ka time chahenge. Kya yeh baat-cheet ke liye sahi time hai?",
            "introduction_time_check"
        )

    def _get_content_consumption_question(self) -> Optional[Tuple[str, str]]:
        """Get content consumption questions in Hinglish"""
        questions = [
            (
                "Aap usually din ke kis time content dekhte hain? "
                "Jaise ki morning, evening, commute ke dauran, ya sone se pehle?",
                "content_watch_time"
            ),
            (
                "Aap typically app par kitna time spend karte hain? "
                "Ek baar jab aap app kholte hain, toh kitna time scroll karte hain ya content dekhte hain?",
                "content_time_spent"
            )
        ]

        if self.current_question_index < len(questions):
            question = questions[self.current_question_index]
            self.current_question_index += 1
            return question
        return None

    def _get_content_preference_question(self) -> Optional[Tuple[str, str]]:
        """Get content preference questions - Only 1 question"""
        # Only ask the first question to keep it short
        if self.current_question_index == 0:
            self.current_question_index += 1
            return (
                "Aap kin categories ya topics mein sabse zyada interest rakhte hain? "
                "Jaise ki business, AI, stock market, ya communication skills?",
                "content_categories"
            )
        return None

    def _get_demography_question(self) -> Optional[Tuple[str, str]]:
        """Get demography questions - Only 1 question"""
        # Only ask occupation to keep it short
        if self.current_question_index == 0:
            self.current_question_index += 1
            return (
                "Aapka occupation kya hai?",
                "demography_occupation"
            )
        return None

    def _get_motivation_question(self) -> Optional[Tuple[str, str]]:
        """Get motivation questions - Only 1 question"""
        # Only ask the first question to keep it short
        if self.current_question_index == 0:
            self.current_question_index += 1
            return (
                "Gyan TV app par content dekhne ke liye aapko kya motivate karta hai?",
                "motivation_watch"
            )
        return None

    def _get_user_experience_question(self) -> Optional[Tuple[str, str]]:
        """Get user experience questions - Only 1 question"""
        # Only ask the first question to keep it short
        if self.current_question_index == 0:
            self.current_question_index += 1
            return (
                "Gyan TV par content ki quality se aap kitne satisfied hain?",
                "ux_satisfaction"
            )
        return None

    def _get_competitor_question(self) -> Optional[Tuple[str, str]]:
        """Get competitor questions - Only 1 question"""
        # Only ask the first question to keep it short
        if self.current_question_index == 0:
            self.current_question_index += 1
            return (
                "Kya aap Gyan TV ke alawa learning ke liye koi aur platform ya YouTube channel use karte hain?",
                "competitor_use_other"
            )
        return None

    def _get_suggestions_question(self) -> Optional[Tuple[str, str]]:
        """Get suggestions questions - Only 1 question"""
        # Only ask the first question to keep it short
        if self.current_question_index == 0:
            self.current_question_index += 1
            return (
                "Agar hum Gyan TV content mein ek cheez improve kar sakte hain, toh woh kya honi chahiye?",
                "suggestions_one_improvement"
            )
        return None

    def save_response(self, question_key: str, response: str, question_text: str = None):
        """Save user response and track conversation"""
        self.responses[question_key] = response

        # Add user response to conversation history
        # Note: Question is already added via add_agent_message() when asked
        # Only add question here if it wasn't added before (fallback)
        if question_text and (not self.conversation_history or
                              self.conversation_history[-1][0] != "Agent" or
                              self.conversation_history[-1][1] != question_text):
            # Add the question that was asked (if not already added)
            self.conversation_history.append(("Agent", question_text))
        # Add the user's response
        self.conversation_history.append(("User", response))

        # Mark introduction as completed after time check
        if question_key == "introduction_time_check":
            response_lower = response.lower()
            if "yes" in response_lower or "yeah" in response_lower or "sure" in response_lower or "ok" in response_lower or "हाँ" in response_lower or "ठीक" in response_lower:
                self.introduction_completed = True
                self.current_section = QuestionnaireSection.CONTENT_CONSUMPTION
                self.current_question_index = 0
            else:
                # If not a good time, mark as completed anyway to move forward
                # In production, you might want to handle this differently
                self.introduction_completed = True
                self.current_section = QuestionnaireSection.CONTENT_CONSUMPTION
                self.current_question_index = 0

    def add_agent_message(self, message: str):
        """Add an agent message to conversation history"""
        self.conversation_history.append(("Agent", message))

    def get_formatted_transcript(self) -> str:
        """Get formatted transcript with Agent/User labels"""
        if not self.conversation_history:
            return ""

        lines = []
        for speaker, text in self.conversation_history:
            lines.append(f"{speaker}: {text}")

        return "\n".join(lines)

    def get_completion_message(self) -> str:
        """Get completion message in Hinglish"""
        return (
            "Aapke time aur valuable feedback ke liye bahut bahut dhanyawad! "
            "Aapki responses humein Gyan TV ko behtar banane mein madad karengi. Aapka din shubh ho!"
        )

    def get_termination_message(self) -> str:
        """Get termination message when user shows disinterest"""
        return (
            "Theek hai, main samajh gaya. Aap busy lag rahe hain. "
            "Koi baat nahi, aap kabhi bhi call kar sakte hain. Dhanyawad aur goodbye!"
        )

    def is_completed(self) -> bool:
        """Check if questionnaire is completed"""
        return self.current_section == QuestionnaireSection.COMPLETED

