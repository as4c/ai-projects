"""
Questionnaire Parser for Decision Tree Structure
Parses questionnaire files and extracts decision tree logic
Supports caching parsed questionnaires to JSON for faster loading during calls
"""
from typing import Dict, List, Optional, Tuple
from pathlib import Path
import re
import json
import os


class QuestionnaireParser:
    """Parse questionnaire files and extract decision tree structure"""

    def __init__(self, event_name: str, language: str = 'hi'):
        self.event_name = event_name
        self.language = language
        self.parsed_tree = {}

    def _get_cache_path(self, questionnaire_dir: Path) -> Path:
        """Get path to cached JSON file"""
        return questionnaire_dir / f"{self.language}_parsed.json"

    def _get_txt_path(self, questionnaire_dir: Path) -> Path:
        """Get path to source txt file"""
        return questionnaire_dir / f"{self.language}.txt"

    def _is_cache_valid(self, cache_path: Path, txt_path: Path) -> bool:
        """Check if cache exists and is newer than source file"""
        if not cache_path.exists():
            return False
        if not txt_path.exists():
            return False
        # Cache is valid if it's newer than the source file
        cache_mtime = os.path.getmtime(cache_path)
        txt_mtime = os.path.getmtime(txt_path)
        return cache_mtime > txt_mtime

    def _load_from_cache(self, cache_path: Path) -> Optional[Dict]:
        """Load parsed questionnaire from cache"""
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            print(f"✅ Loaded questionnaire from cache: {cache_path}")
            return data
        except Exception as e:
            print(f"⚠️ Failed to load cache: {e}")
            return None

    def _save_to_cache(self, tree: Dict, cache_path: Path) -> bool:
        """Save parsed questionnaire to cache"""
        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(tree, f, ensure_ascii=False, indent=2)
            print(f"✅ Saved parsed questionnaire to cache: {cache_path}")
            return True
        except Exception as e:
            print(f"⚠️ Failed to save cache: {e}")
            return False

    def parse(self, force_reparse: bool = False) -> Dict:
        """
        Parse questionnaire file and return decision tree structure.
        Uses cached JSON if available and up-to-date.

        Args:
            force_reparse: If True, ignore cache and reparse from txt file
        """
        try:
            # Get the base directory (ai_researcher folder)
            base_dir = Path(__file__).parent.parent  # ai_researcher/
            questionnaire_dir = base_dir / "questionnaires" / self.event_name

            print(f"DEBUG: Looking for questionnaire in: {questionnaire_dir}")

            if not questionnaire_dir.exists():
                print(f"❌ Questionnaire directory not found: {questionnaire_dir}")
                return {}

            # Get file paths
            txt_path = self._get_txt_path(questionnaire_dir)
            cache_path = self._get_cache_path(questionnaire_dir)

            # Try to load from cache first (unless force_reparse)
            if not force_reparse and self._is_cache_valid(cache_path, txt_path):
                cached_tree = self._load_from_cache(cache_path)
                if cached_tree:
                    print(f"📋 Using cached questionnaire ({len(cached_tree.get('questions', {}))} questions)")
                    return cached_tree

            # If no valid cache, parse from txt file
            print(f"🔄 Parsing questionnaire from txt file...")

            # Try language-specific file first, then fallback to English
            if not txt_path.exists():
                en_file = questionnaire_dir / "en.txt"
                if en_file.exists():
                    txt_path = en_file
                    print(f"Language file {self.language}.txt not found, using en.txt")
                else:
                    print(f"❌ Questionnaire file not found: {txt_path} or {en_file}")
                    if questionnaire_dir.exists():
                        print(f"Files in directory: {list(questionnaire_dir.iterdir())}")
                    return {}

            with open(txt_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse based on event_name
            if self.event_name == "subscription_cancelled":
                tree = self._parse_subscription_cancelled(content)
            else:
                tree = self._parse_generic(content)

            # Save to cache for future use
            if tree and tree.get("questions"):
                self._save_to_cache(tree, cache_path)

            return tree

        except Exception as e:
            print(f"Error parsing questionnaire: {e}")
            import traceback
            traceback.print_exc()
            return {}

    @classmethod
    def rebuild_cache(cls, event_name: str, language: str = 'hi') -> bool:
        """
        Force rebuild the cache for a questionnaire.
        Call this when you update the txt file.
        """
        parser = cls(event_name, language)
        tree = parser.parse(force_reparse=True)
        return bool(tree and tree.get("questions"))

    @classmethod
    def rebuild_all_caches(cls) -> Dict[str, bool]:
        """
        Rebuild caches for all questionnaires in all languages.
        Returns dict of {event_name/language: success}
        """
        base_dir = Path(__file__).parent.parent / "questionnaires"
        results = {}

        if not base_dir.exists():
            print(f"Questionnaires directory not found: {base_dir}")
            return results

        for event_dir in base_dir.iterdir():
            if event_dir.is_dir():
                event_name = event_dir.name
                for txt_file in event_dir.glob("*.txt"):
                    language = txt_file.stem  # e.g., "hi" from "hi.txt"
                    if language.endswith("_parsed"):
                        continue  # Skip cache files
                    key = f"{event_name}/{language}"
                    print(f"Rebuilding cache for {key}...")
                    results[key] = cls.rebuild_cache(event_name, language)

        return results

    def _parse_subscription_cancelled(self, content: str) -> Dict:
        """Parse subscription cancellation questionnaire with decision tree (simplified format)"""
        tree = {
            "questions": {},
            "pathways": {
                "pricing": [],
                "content": [],
                "lack_of_use": [],
                "technical": [],
                "clarification": []
            },
            "opening": "",
            "closing": "",
            "sections": {}
        }

        lines = content.split('\n')
        current_question_id = None
        current_pathway = None
        current_mode = None  # 'opening', 'question', 'routing', 'followup', 'closing'

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Skip empty lines
            if not line:
                i += 1
                continue

            # Detect mode markers
            if line.upper() == "OPENING":
                current_mode = "opening"
                i += 1
                continue
            elif line.upper() == "CLOSING":
                current_mode = "closing"
                i += 1
                continue
            elif line.upper() == "ROUTING":
                current_mode = "routing"
                i += 1
                continue
            elif line.upper().startswith("PATHWAY "):
                pathway_name = line.split()[1].lower()
                current_pathway = pathway_name
                current_mode = "pathway"
                i += 1
                continue
            elif line.upper().startswith("FOLLOWUP "):
                followup_qid = line.split()[1].lower()
                current_question_id = followup_qid
                current_mode = "followup"
                i += 1
                continue

            # Handle content based on current mode
            if current_mode == "opening":
                # Stop opening mode if we hit a question ID or other marker
                if re.match(r'^(Q\d+[a-z]?)$', line, re.IGNORECASE):
                    current_mode = None  # Reset mode, will be handled by question detection
                    # Don't increment i, let question detection handle it
                    continue
                if not tree["opening"]:
                    tree["opening"] = line
                else:
                    tree["opening"] += " " + line
                i += 1
                continue
            elif current_mode == "closing":
                if not tree["closing"]:
                    tree["closing"] = line
                else:
                    tree["closing"] += " " + line
                i += 1
                continue
            elif current_mode == "routing":
                # Parse routing conditions: "cost → q2a"
                if "→" in line or "->" in line:
                    parts = re.split(r'[→\->]', line, 1)
                    if len(parts) == 2:
                        trigger = parts[0].strip()
                        next_q = parts[1].strip().lower()
                        # Routing applies to the most recent question (usually Q1)
                        if current_question_id and current_question_id in tree["questions"]:
                            if not tree["questions"][current_question_id].get("conditions"):
                                tree["questions"][current_question_id]["conditions"] = {}
                            tree["questions"][current_question_id]["conditions"][trigger] = next_q
                            print(f"✅ Added routing condition '{trigger}' → '{next_q}' to question {current_question_id}")
                        elif "q1" in tree["questions"]:
                            # Default to Q1 if no current question
                            if not tree["questions"]["q1"].get("conditions"):
                                tree["questions"]["q1"]["conditions"] = {}
                            tree["questions"]["q1"]["conditions"][trigger] = next_q
                            print(f"✅ Added routing condition '{trigger}' → '{next_q}' to Q1 (default)")
                        else:
                            print(f"⚠️ Warning: Could not find Q1 to add routing condition '{trigger}' → '{next_q}'")
                    i += 1
                    continue
                else:
                    # Not a routing condition - exit routing mode and let other handlers process
                    print(f"🔄 Exiting routing mode, line '{line[:30]}...' is not a routing condition")
                    current_mode = None
                    # Don't increment i, let other handlers process this line
                    # Fall through to question detection below
            elif current_mode == "followup":
                # Check if this line is a new question ID - if so, exit followup mode
                if re.match(r'^(Q\d+[a-z]?)$', line, re.IGNORECASE):
                    print(f"🔄 Exiting followup mode, found new question: {line}")
                    current_mode = None
                    # Don't increment i, let question detection handle it
                    # Fall through to question detection below
                else:
                    # Add follow-up to current question
                    if current_question_id and current_question_id in tree["questions"]:
                        tree["questions"][current_question_id]["follow_ups"].append(line)
                    i += 1
                    continue

            # Detect question IDs (Q1, Q2a, Q2b, etc.) - simple format
            question_match = re.match(r'^(Q\d+[a-z]?)$', line, re.IGNORECASE)
            if question_match:
                question_id = question_match.group(1).lower()
                current_question_id = question_id
                current_mode = "question"

                print(f"🔍 Found question ID: {question_id} at line {i}")

                # Get question text from next line
                question_text = ""
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    print(f"   Next line ({i+1}): '{next_line[:60]}...' if len > 60 else '{next_line}'")

                    # Check if next line is a marker or another question ID
                    # Allow lines that start with Q only if they're question IDs (will be handled separately)
                    if next_line and not next_line.upper().startswith(("ROUTING", "PATHWAY", "FOLLOWUP", "CLOSING", "OPENING")):
                        # Check if it's another question ID (Q followed by number)
                        if not re.match(r'^(Q\d+[a-z]?)$', next_line, re.IGNORECASE):
                            question_text = next_line
                            i += 1  # Skip the question text line
                            print(f"   ✅ Extracted question text: '{question_text[:50]}...'")
                        else:
                            print(f"   ⚠️ Next line is a question ID, no text for {question_id}")
                    else:
                        print(f"   ⚠️ Next line is a marker or empty, no text for {question_id}")
                else:
                    print(f"   ⚠️ No next line available for {question_id}")

                # Determine pathway based on question ID
                if question_id.startswith('q2a'):
                    current_pathway = "pricing"
                elif question_id.startswith('q2b'):
                    current_pathway = "content"
                elif question_id.startswith('q2c'):
                    current_pathway = "lack_of_use"
                elif question_id.startswith('q2d'):
                    current_pathway = "technical"
                elif question_id == 'q1a':
                    current_pathway = "clarification"
                else:
                    current_pathway = None

                # Store question
                if question_text:
                    tree["questions"][question_id] = {
                        "id": question_id,
                        "text": question_text,
                        "section": None,
                        "pathway": current_pathway,
                        "follow_ups": [],
                        "conditions": None
                    }
                    print(f"   ✅ Stored question {question_id} in tree")

                    # Add to pathway if applicable
                    if current_pathway:
                        tree["pathways"][current_pathway].append(question_id)
                else:
                    print(f"   ❌ Warning: Question {question_id} has no text - NOT storing")

                i += 1
                continue

            i += 1

            # Detect sections
            if line.startswith('###') or line.startswith('##'):
                section_match = re.search(r'###?\s*\*\*(.+?)\*\*|###?\s*(.+?)$', line)
                if section_match:
                    current_section = section_match.group(1) or section_match.group(2)
                    tree["sections"][current_section] = []

            # Detect opening script
            if 'Opening Script' in line or 'OPENING' in line.upper() or 'Agent Introduction' in line:
                i += 1
                opening_lines = []
                while i < len(lines) and not lines[i].strip().startswith('---') and not lines[i].strip().startswith('**'):
                    line_text = lines[i].strip()
                    # Skip empty lines, bullet points, and section headers
                    if line_text and not line_text.startswith('*') and not line_text.startswith('**') and ':' not in line_text:
                        # Extract quoted text if present
                        if line_text.startswith('"') or line_text.startswith('"'):
                            # Remove quotes
                            line_text = re.sub(r'^["""]+|["""]+$', '', line_text)
                        opening_lines.append(line_text)
                    i += 1
                # Join and clean up
                opening_text = " ".join(opening_lines).strip()
                # Remove any remaining quotes
                opening_text = re.sub(r'^["""]+|["""]+$', '', opening_text)
                tree["opening"] = opening_text
                print(f"DEBUG: Parsed opening text: {opening_text[:100]}...")
                continue

            # Detect closing
            if 'CLOSING' in line.upper() or 'Closing' in line:
                i += 1
                closing_lines = []
                while i < len(lines) and lines[i].strip() and not lines[i].strip().startswith('###'):
                    if lines[i].strip() and not lines[i].strip().startswith('*'):
                        closing_lines.append(lines[i].strip())
                    i += 1
                tree["closing"] = " ".join(closing_lines)
                continue

            # Detect question IDs (Q1, Q2a, Q2b, etc.)
            # Match: **Q2a:** or Q2a: or Q2a: text
            question_match = re.match(r'^(\*\*)?(Q\d+[a-z]?):?\s*(.*)$', line, re.IGNORECASE)
            if question_match:
                # Keep question ID in lowercase for consistency (Q2a, not Q2A)
                question_id = question_match.group(2).lower()
                question_label = question_match.group(3).strip() if question_match.group(3) else ""

                # Remove markdown formatting from label
                question_label = re.sub(r'\*\*', '', question_label)

                # The actual question text might be on the next line (in quotes)
                # Always check next line(s) for quoted question text
                # This handles cases like "**Q2a:**" followed by "question text"
                question_text = None

                # Look ahead 1-3 lines for the actual question text
                for j in range(i + 1, min(i + 4, len(lines))):
                    next_line = lines[j].strip()
                    # Skip empty lines
                    if not next_line:
                        continue
                    # Stop at section markers (---)
                    if next_line.startswith('---'):
                        break

                    # Priority 1: Check if line starts with quote (most common - direct question)
                    if next_line.startswith('"') or next_line.startswith('"') or next_line.startswith('"'):
                        # Extract quoted text - handle both opening and closing quotes
                        quote_match = re.match(r'^["""](.+?)["""]$', next_line)
                        if quote_match:
                            question_text = quote_match.group(1).strip()
                            i = j  # Move past this line
                            break
                        else:
                            # Try to extract even if quotes don't match perfectly
                            cleaned = re.sub(r'^["""]+|["""]+$', '', next_line)
                            if cleaned and len(cleaned) > 10:  # Reasonable question length
                                question_text = cleaned.strip()
                                i = j
                                break

                    # Priority 2: Check if line contains quoted text (bullet point with quote)
                    elif '"' in next_line or '"' in next_line:
                        quote_match = re.search(r'["""](.+?)["""]', next_line)
                        if quote_match:
                            extracted = quote_match.group(1).strip()
                            if len(extracted) > 10:  # Reasonable question length
                                question_text = extracted
                                i = j
                                break

                # If no quoted text found, use the label (but filter out non-question labels)
                if not question_text:
                    # Only use label if it's not a known non-question label
                    if question_label and question_label not in ["Open-Ended Discovery", "Clarification (agar jawab vague ho)"]:
                        question_text = question_label
                    elif question_label in ["Open-Ended Discovery", "Clarification (agar jawab vague ho)"]:
                        # For these labels, we must find the actual question text
                        # Continue searching further (up to 6 lines ahead)
                        for j in range(i + 1, min(i + 7, len(lines))):
                            potential_question = lines[j].strip()
                            if not potential_question or potential_question.startswith('---'):
                                continue
                            # Check for quoted text
                            if potential_question.startswith('"') or potential_question.startswith('"') or potential_question.startswith('"'):
                                quote_match = re.match(r'^["""](.+?)["""]$', potential_question)
                                if quote_match:
                                    question_text = quote_match.group(1).strip()
                                    i = j
                                    break
                                else:
                                    cleaned = re.sub(r'^["""]+|["""]+$', '', potential_question)
                                    if cleaned and len(cleaned) > 10:
                                        question_text = cleaned.strip()
                                        i = j
                                        break

                # Clean up question text - remove any remaining quotes
                if question_text:
                    question_text = re.sub(r'^["""]+|["""]+$', '', question_text)
                    question_text = question_text.strip()

                # Final fallback - if still no good text, skip this question
                if not question_text or len(question_text) < 5:
                    print(f"Warning: Could not extract question text for {question_id}, skipping")
                    i += 1
                    continue

                current_question_id = question_id

                # Determine pathway based on question ID (case-insensitive)
                question_id_lower = question_id.lower()
                if question_id_lower.startswith('q2a'):
                    current_pathway = "pricing"
                elif question_id_lower.startswith('q2b'):
                    current_pathway = "content"
                elif question_id_lower.startswith('q2c'):
                    current_pathway = "lack_of_use"
                elif question_id_lower.startswith('q2d'):
                    current_pathway = "technical"
                elif question_id_lower == 'q1a':
                    current_pathway = "clarification"
                else:
                    current_pathway = None

                # Store question
                tree["questions"][question_id] = {
                    "id": question_id,
                    "text": question_text,
                    "section": current_section,
                    "pathway": current_pathway,
                    "follow_ups": [],
                    "conditions": None
                }

                # Add to pathway if applicable
                if current_pathway:
                    tree["pathways"][current_pathway].append(question_id)

                # Check for pathway definition
                if 'PATHWAY' in line.upper():
                    pathway_match = re.search(r'PATHWAY\s+([A-Z]):', line, re.IGNORECASE)
                    if pathway_match:
                        pathway_letter = pathway_match.group(1).upper()
                        pathway_map = {
                            'A': 'pricing',
                            'B': 'content',
                            'C': 'lack_of_use',
                            'D': 'technical'
                        }
                        current_pathway = pathway_map.get(pathway_letter)

            # Detect pathway routing instructions
            elif 'Agent Notes' in line or 'Follow-up Pathways' in line or 'If user mentions' in line.lower():
                i += 1
                # Read next few lines for routing logic
                routing_lines = []
                while i < len(lines) and i < len(lines) and not lines[i].strip().startswith('**') and not lines[i].strip().startswith('Q'):
                    routing_line = lines[i].strip()
                    if routing_line and not routing_line.startswith('*') and not routing_line.startswith('●'):
                        routing_lines.append(routing_line)
                    i += 1

                # Parse routing conditions
                if current_question_id and current_question_id.lower() == 'q1':
                    conditions = {
                        "cost": "q2a",
                        "content": "q2b",
                        "lack of use": "q2c",
                        "vague": "q1a",
                        "technical": "q2d"
                    }
                    # Use lowercase question_id for consistency
                    qid_lower = current_question_id.lower()
                    if qid_lower in tree["questions"]:
                        tree["questions"][qid_lower]["conditions"] = conditions
                    elif current_question_id in tree["questions"]:
                        tree["questions"][current_question_id]["conditions"] = conditions
                i -= 1  # Backtrack one line

            # Detect follow-up questions
            elif line.startswith('*') or line.startswith('●') or line.startswith('○'):
                followup_text = re.sub(r'^[\*\●\○\-\s]+', '', line)
                followup_text = re.sub(r'^\*\*|\*\*$', '', followup_text)
                followup_text = re.sub(r'^"|"$', '', followup_text)

                if followup_text and current_question_id:
                    # Check if it's a conditional follow-up
                    if 'Agar' in followup_text or 'If' in followup_text:
                        # Extract condition and question
                        condition_match = re.search(r'(Agar|If)\s+(.+?)\s+(toh|then|→)', followup_text, re.IGNORECASE)
                        if condition_match:
                            condition = condition_match.group(2).strip()
                            # This is a conditional, store it
                            if current_question_id not in tree["questions"]:
                                continue
                            if "conditional_followups" not in tree["questions"][current_question_id]:
                                tree["questions"][current_question_id]["conditional_followups"] = []
                            tree["questions"][current_question_id]["conditional_followups"].append({
                                "condition": condition,
                                "text": followup_text
                            })
                    else:
                        # Regular follow-up
                        if current_question_id in tree["questions"]:
                            tree["questions"][current_question_id]["follow_ups"].append(followup_text)

            # Detect regular question text (without Q prefix)
            elif '?' in line and not line.startswith('*') and not line.startswith('●'):
                # This might be a question without explicit ID
                question_text = re.sub(r'^\*\*|\*\*$', '', line)
                question_text = re.sub(r'^"|"$', '', question_text)

                # Check if it's part of a section or standalone
                if current_section and question_text:
                    # Try to infer question ID from context
                    if not current_question_id:
                        # Create a question ID based on section
                        section_num = len(tree["questions"]) + 1
                        current_question_id = f"Q{section_num}"
                        tree["questions"][current_question_id] = {
                            "id": current_question_id,
                            "text": question_text,
                            "section": current_section,
                            "pathway": current_pathway,
                            "follow_ups": [],
                            "conditions": None
                        }
                    else:
                        # Add as follow-up to current question
                        if current_question_id in tree["questions"]:
                            tree["questions"][current_question_id]["follow_ups"].append(question_text)

            i += 1

        # Normalize question IDs to lowercase for consistency
        normalized_questions = {}
        for qid, q_data in tree["questions"].items():
            normalized_qid = qid.lower()
            normalized_questions[normalized_qid] = q_data
            q_data["id"] = normalized_qid  # Update ID to lowercase

        tree["questions"] = normalized_questions

        # Normalize pathway question IDs too
        for pathway_name, question_ids in tree["pathways"].items():
            normalized_ids = []
            for qid in question_ids:
                normalized_ids.append(qid.lower())
            tree["pathways"][pathway_name] = normalized_ids

        # Normalize conditions in questions
        for qid, q_data in tree["questions"].items():
            if q_data.get("conditions"):
                normalized_conditions = {}
                for trigger, next_q in q_data["conditions"].items():
                    normalized_conditions[trigger] = next_q.lower()
                q_data["conditions"] = normalized_conditions

        # Set default first question
        if "q1" not in tree["questions"]:
            # Try to find first question
            for qid in sorted(tree["questions"].keys()):
                tree["questions"][qid]["is_first"] = True
                break

        # Mark Q1 as first question
        if "q1" in tree["questions"]:
            tree["questions"]["q1"]["is_first"] = True

        print(f"Parsed {len(tree['questions'])} questions for {self.event_name}")
        print(f"Question IDs: {list(tree['questions'].keys())}")
        return tree

    def _parse_generic(self, content: str) -> Dict:
        """Generic parser for other questionnaire types"""
        tree = {
            "questions": {},
            "pathways": {},
            "opening": "",
            "closing": ""
        }

        # Simple extraction of questions
        lines = content.split('\n')
        questions = []

        for line in lines:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('●') or line.startswith('*'):
                continue
            if '?' in line:
                questions.append(line)

        # Create question IDs
        for idx, question_text in enumerate(questions[:5], 1):  # Limit to 5
            qid = f"Q{idx}"
            tree["questions"][qid] = {
                "id": qid,
                "text": question_text,
                "section": None,
                "pathway": None,
                "follow_ups": [],
                "conditions": None
            }

        return tree

