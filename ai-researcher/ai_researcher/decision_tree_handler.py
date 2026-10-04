"""
Decision Tree Handler for Questionnaire Flow
Manages questionnaire flow with conditional branching based on user responses
"""
from typing import Dict, Optional, List, Tuple
from .questionnaire_parser import QuestionnaireParser
from .response_analyzer import ResponseAnalyzer


class DecisionTreeHandler:
    """Handle decision tree-based questionnaire flow"""

    def __init__(self, event_name: str, language: str = 'hi', user_name: str = None,
                 user_gender: str = None, user_age: str = None):
        self.event_name = event_name
        self.language = language
        self.user_name = user_name
        self.user_gender = user_gender
        self.user_age = user_age

        # Parse questionnaire
        parser = QuestionnaireParser(event_name, language)
        self.tree = parser.parse()

        # Initialize analyzer - skip LLM for faster responses
        # LLM is only needed for truly ambiguous cases, keyword matching covers 90%+
        self.analyzer = ResponseAnalyzer(skip_llm=False)  # Set to True to always skip LLM

        # State management
        self.current_question_id = None
        self.visited_questions = set()
        self.pathway = None
        self.pathway_history = []
        self.responses: Dict[str, str] = {}
        self.conversation_history: List[Tuple[str, str]] = []
        self.total_questions_asked = 0
        self.MAX_QUESTIONS = 5

        # Track if introduction/consent is completed
        self.introduction_completed = False
        self.consent_given = False

    def get_next_question(self, user_response: str = None) -> Optional[Tuple[str, str]]:
        """
        Get next question based on current state and user response

        Args:
            user_response: User's response to previous question (if any)

        Returns:
            Tuple of (question_text, question_key) or None if completed
        """
        # Check question limit
        if self.total_questions_asked >= self.MAX_QUESTIONS:
            return None

        # Handle introduction/consent first
        if not self.introduction_completed:
            return self._get_opening_question()

        # If user response provided, analyze and route
        if user_response and self.current_question_id:
            # Special handling for opening question - just move to Q1 if user agrees
            # Handle both "OPENING" and "opening" cases
            if self.current_question_id.upper() == "OPENING":
                # Save opening response
                self.responses[self.current_question_id] = user_response
                self.conversation_history.append(("User", user_response))
                self.visited_questions.add(self.current_question_id)

                # Check if user agreed (yes, haan, etc.)
                response_lower = user_response.lower()
                affirmative_words = ["yes", "yeah", "yep", "ok", "okay", "haan", "हाँ", "ठीक", "sure", "bilkul", "बिल्कुल", "ji", "जी"]

                print(f"🔍 DEBUG: Checking opening response: '{user_response}'")
                print(f"🔍 DEBUG: Available questions in tree: {list(self.tree.get('questions', {}).keys())}")

                if any(word in response_lower for word in affirmative_words):
                    # User agreed, move to Q1 (use lowercase)
                    print(f"✅ User agreed to opening question, moving to Q1")
                    self.current_question_id = None  # Reset to get Q1
                    next_q = self._get_question_by_id("q1")
                    if not next_q:
                        print(f"❌ ERROR: Could not get Q1 after opening question")
                        print(f"❌ Tree questions: {self.tree.get('questions', {})}")
                    else:
                        print(f"✅ Got Q1: {next_q[0][:50]}...")
                    return next_q
                else:
                    # User declined or unclear, still move to Q1 but note it
                    print(f"⚠️ User response to opening was not clearly affirmative: {user_response}, but moving to Q1 anyway")
                    self.current_question_id = None
                    next_q = self._get_question_by_id("q1")
                    if not next_q:
                        print(f"❌ ERROR: Could not get Q1 after opening question")
                        print(f"❌ Tree questions: {self.tree.get('questions', {})}")
                    else:
                        print(f"✅ Got Q1: {next_q[0][:50]}...")
                    return next_q

            # For regular questions (Q1, Q2a, etc.), analyze and route
            analysis = self.analyzer.analyze_response(user_response, self.current_question_id)

            # Save response
            self.responses[self.current_question_id] = user_response
            self.conversation_history.append(("User", user_response))

            # Route to next question based on analysis
            next_question_id = analysis.get("next_question_id")
            self.pathway = analysis.get("pathway")
            self.pathway_history.append({
                "question_id": self.current_question_id,
                "pathway": self.pathway,
                "confidence": analysis.get("confidence")
            })

            # Mark current question as visited
            self.visited_questions.add(self.current_question_id)

            # Special handling: If we're at Q1a (clarification) and response is still unclear,
            # don't loop back to Q1a - move to Q3 (general question) instead
            if self.current_question_id == "q1a":
                if next_question_id == "q1a" or next_question_id is None or self.pathway == "clarification":
                    print(f"⚠️ Still unclear after Q1a, moving to Q3 (general question) instead of looping")
                    next_question_id = "q3"

            # Also prevent asking the same question we just asked
            if next_question_id and next_question_id in self.visited_questions:
                print(f"⚠️ Question {next_question_id} already asked, finding alternative...")
                # Try to find next unasked question in order
                question_priority = ["q2a", "q2b", "q2c", "q2d", "q3", "q4"]
                for qid in question_priority:
                    if qid not in self.visited_questions and qid in self.tree.get("questions", {}):
                        next_question_id = qid
                        print(f"   → Moving to {qid} instead")
                        break

            # Get next question
            return self._get_question_by_id(next_question_id)

        # If no response, get first question (Q1) - use lowercase
        if not self.current_question_id:
            return self._get_question_by_id("q1")

        # Get next sequential question in current pathway
        return self._get_next_sequential_question()

    def _get_opening_question(self) -> Tuple[str, str]:
        """Get opening/introduction question"""
        opening_text = self.tree.get("opening", "")

        # Personalize opening if user name provided
        if self.user_name:
            # Extract first name (split by space and take first part)
            first_name = self.user_name.split()[0] if self.user_name else self.user_name
            print(f"DEBUG: Replacing placeholders with first name: '{first_name}' (from full name: '{self.user_name}')")
            print(f"DEBUG: Opening text before replacement: {opening_text[:100]}...")

            # Replace various placeholder formats
            opening_text = opening_text.replace("[User Name]", first_name)
            opening_text = opening_text.replace("[User First Name]", first_name)
            opening_text = opening_text.replace("[First Name]", first_name)
            opening_text = opening_text.replace("[Name]", first_name)

            print(f"DEBUG: Opening text after name replacement: {opening_text[:100]}...")

            # Handle gender-specific pronouns
            # The text has "raha/rahi" format - replace with correct gender
            is_female = self.user_gender and self.user_gender.lower() in ['female', 'f', 'woman', 'madam', 'ma\'am', 'mrs', 'miss', 'ms']
            is_male = self.user_gender and self.user_gender.lower() in ['male', 'm', 'man', 'sir', 'mr']

            print(f"DEBUG: Gender detected - is_female: {is_female}, is_male: {is_male}, raw gender: '{self.user_gender}'")

            if is_female:
                # Female pronouns
                opening_text = opening_text.replace("raha/rahi", "rahi")
                opening_text = opening_text.replace("sakta/sakti", "sakti")
                opening_text = opening_text.replace("kar raha", "kar rahi")
                opening_text = opening_text.replace("sakta", "sakti")
                print(f"DEBUG: Applied female pronouns")
            elif is_male:
                # Male pronouns
                opening_text = opening_text.replace("raha/rahi", "raha")
                opening_text = opening_text.replace("sakta/sakti", "sakta")
                opening_text = opening_text.replace("kar rahi", "kar raha")  # Just in case
                print(f"DEBUG: Applied male pronouns")
            else:
                # Default to male if gender not specified
                opening_text = opening_text.replace("raha/rahi", "raha")
                opening_text = opening_text.replace("sakta/sakti", "sakta")
                print(f"DEBUG: Gender not specified, defaulting to male pronouns")

            print(f"DEBUG: Opening text after gender replacement: {opening_text[:100]}...")

        if not opening_text:
            # Fallback opening
            opening_text = "Hello, main GyanTV se baat kar rahi hoon. Kya aap mere saath 3 minute baat kar sakte hain?"

        self.introduction_completed = True
        self.current_question_id = "OPENING"
        self.total_questions_asked += 1
        self.conversation_history.append(("Agent", opening_text))

        return (opening_text, "opening")

    def _get_question_by_id(self, question_id: str) -> Optional[Tuple[str, str]]:
        """Get question text by question ID"""
        questions = self.tree.get("questions", {})
        if question_id not in questions:
            print(f"❌ Question ID {question_id} not found in tree")
            print(f"Available questions: {list(questions.keys())}")
            print(f"Total questions asked so far: {self.total_questions_asked}/{self.MAX_QUESTIONS}")
            # Try to find a similar question or return None
            return None

        question_data = self.tree["questions"][question_id]
        question_text = question_data.get("text", "")

        if not question_text:
            print(f"❌ Question {question_id} has no text")
            return None

        # Check if we've reached max questions
        if self.total_questions_asked >= self.MAX_QUESTIONS:
            print(f"⚠️ Max questions ({self.MAX_QUESTIONS}) reached, cannot ask {question_id}")
            return None

        # Mark as visited and update state
        self.visited_questions.add(question_id)
        self.current_question_id = question_id
        self.total_questions_asked += 1

        # Update pathway if question has one
        if question_data.get("pathway"):
            self.pathway = question_data["pathway"]

        # Add to conversation history
        self.conversation_history.append(("Agent", question_text))

        print(f"✅ Returning question {question_id}: {question_text[:50]}...")
        return (question_text, question_id)

    def _get_next_sequential_question(self) -> Optional[Tuple[str, str]]:
        """Get next sequential question in current pathway or general flow"""
        questions = self.tree.get("questions", {})

        # If we have a pathway, try to get next question in that pathway
        if self.pathway:
            pathway_questions = self.tree.get("pathways", {}).get(self.pathway, [])
            for qid in pathway_questions:
                if qid not in self.visited_questions:
                    return self._get_question_by_id(qid)

        # Otherwise, get next unvisited question in order (use lowercase IDs)
        question_order = ["q1", "q1a", "q2a", "q2b", "q2c", "q2d", "q3", "q4"]
        for qid in question_order:
            if qid in questions and qid not in self.visited_questions:
                return self._get_question_by_id(qid)

        # If all questions visited, check for follow-ups
        if self.current_question_id:
            current_question = questions.get(self.current_question_id, {})
            follow_ups = current_question.get("follow_ups", [])
            if follow_ups:
                # Return first follow-up
                followup_text = follow_ups[0]
                self.conversation_history.append(("Agent", followup_text))
                self.total_questions_asked += 1
                return (followup_text, f"{self.current_question_id}_followup_1")

        return None

    def save_response(self, question_key: str, response: str, question_text: str = None):
        """Save user response"""
        self.responses[question_key] = response
        if question_text:
            # Ensure question is in history
            if not self.conversation_history or self.conversation_history[-1][1] != question_text:
                self.conversation_history.append(("Agent", question_text))
        self.conversation_history.append(("User", response))

    def add_agent_message(self, message: str):
        """Add agent message to conversation history"""
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
        """Get completion message"""
        closing = self.tree.get("closing", "")
        if closing:
            return closing

        # Fallback closing
        return "Dil se thank you, itni honestly baat karne ke liye. Aapka feedback hamare liye bahut valuable hai."

    def get_termination_message(self) -> str:
        """Get termination message when user shows disinterest"""
        return "Theek hai, main samajh gaya. Aap busy lag rahe hain. Koi baat nahi, dhanyawad aur goodbye!"

    def is_completed(self) -> bool:
        """Check if questionnaire is completed"""
        # Check if we've reached max questions or no more questions available
        if self.total_questions_asked >= self.MAX_QUESTIONS:
            return True

        # Check if we've asked all main questions (use lowercase IDs)
        main_questions = ["q1", "q2a", "q2b", "q2c", "q2d", "q3", "q4"]
        if all(qid in self.visited_questions for qid in main_questions if qid in self.tree.get("questions", {})):
            return True

        return False
