#!/usr/bin/env python
"""
Decision Tree Analysis Script
Analyzes and visualizes the decision tree structure from questionnaire files
"""
import os
import sys
import django
from pathlib import Path

# Setup Django - need to add parent directory to path
script_dir = Path(__file__).parent  # ai_researcher/
parent_dir = script_dir.parent      # ai_3/
sys.path.insert(0, str(parent_dir))
sys.path.insert(0, str(script_dir))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_researcher.settings')
django.setup()

# Import after Django setup - modules are in ai_researcher/ai_researcher/
from ai_researcher.questionnaire_parser import QuestionnaireParser
from ai_researcher.response_analyzer import ResponseAnalyzer
import json


def print_section(title, char="=", width=80):
    """Print a formatted section header"""
    print(f"\n{char * width}")
    print(f"{title:^{width}}")
    print(f"{char * width}\n")


def analyze_questionnaire(event_name: str, language: str = 'hi'):
    """Analyze a questionnaire and display its decision tree structure"""

    print_section(f"Decision Tree Analysis: {event_name} ({language})")

    # Parse questionnaire
    print(f"📋 Parsing questionnaire: {event_name} ({language})...")
    parser = QuestionnaireParser(event_name, language)
    tree = parser.parse()

    if not tree:
        print(f"❌ Failed to parse questionnaire")
        return

    # Display basic info
    print_section("Basic Information", "-")
    print(f"Event Name: {event_name}")
    print(f"Language: {language}")
    print(f"Total Questions: {len(tree.get('questions', {}))}")
    print(f"Total Pathways: {len([p for p in tree.get('pathways', {}).values() if p])}")

    # Display opening
    print_section("Opening Script", "-")
    opening = tree.get('opening', 'Not found')
    print(f"{opening}\n")

    # Display questions
    print_section("Questions Structure", "-")
    questions = tree.get('questions', {})

    for qid in sorted(questions.keys()):
        q_data = questions[qid]
        print(f"\n📌 {qid}: {q_data.get('text', 'No text')[:80]}...")
        print(f"   Section: {q_data.get('section', 'N/A')}")
        print(f"   Pathway: {q_data.get('pathway', 'None')}")
        if q_data.get('conditions'):
            print(f"   Conditions: {q_data.get('conditions')}")
        if q_data.get('follow_ups'):
            print(f"   Follow-ups: {len(q_data.get('follow_ups', []))} items")

    # Display pathways
    print_section("Pathways", "-")
    pathways = tree.get('pathways', {})

    for pathway_name, question_ids in pathways.items():
        if question_ids:
            print(f"\n🛤️  Pathway: {pathway_name.upper()}")
            print(f"   Questions: {', '.join(question_ids)}")
            for qid in question_ids:
                if qid in questions:
                    q_text = questions[qid].get('text', 'No text')
                    print(f"      - {qid}: {q_text[:60]}...")

    # Display routing logic
    print_section("Routing Logic", "-")
    print("\nQ1 Response → Pathway Mapping:")
    q1 = questions.get('q1') or questions.get('Q1')
    if q1 and q1.get('conditions'):
        conditions = q1.get('conditions', {})
        for trigger, next_q in conditions.items():
            print(f"   '{trigger}' → {next_q}")
    else:
        print("   No explicit routing conditions found in Q1")

    # Test response analyzer
    print_section("Response Analyzer Test", "-")
    analyzer = ResponseAnalyzer()

    test_responses = [
        ("paisa zyada hai", "pricing"),
        ("cost bahut hai", "pricing"),
        ("content accha nahi", "content"),
        ("courses relevant nahi", "content"),
        ("use nahi kiya", "lack_of_use"),
        ("time nahi mila", "lack_of_use"),
        ("technical problem", "technical"),
        ("bug aaya", "technical"),
        ("yes", "clarification"),
        ("bas", "clarification"),
    ]

    print("\nTesting Intent Classification:")
    for response, expected_pathway in test_responses:
        analysis = analyzer.analyze_response(response, "q1")
        pathway = analysis.get('pathway')
        confidence = analysis.get('confidence', 0)
        next_q = analysis.get('next_question_id')
        status = "✅" if pathway == expected_pathway else "❌"
        print(f"   {status} '{response}' → {pathway} (confidence: {confidence:.2f}) → {next_q}")

    # Display closing
    print_section("Closing Script", "-")
    closing = tree.get('closing', 'Not found')
    print(f"{closing}\n")

    # Save JSON structure
    print_section("Export", "-")
    output_file = f"decision_tree_{event_name}_{language}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(tree, f, indent=2, ensure_ascii=False)
    print(f"✅ Decision tree structure saved to: {output_file}")

    # Validation
    print_section("Validation", "-")
    issues = []

    # Check if Q1 exists (case-insensitive)
    if 'q1' not in questions and 'Q1' not in questions:
        issues.append("❌ Q1 not found")
    else:
        print("✅ Q1 found")

    # Check if pathways have questions
    for pathway_name, question_ids in pathways.items():
        if pathway_name != 'clarification' and not question_ids:
            issues.append(f"⚠️  Pathway '{pathway_name}' has no questions")
        else:
            print(f"✅ Pathway '{pathway_name}' has {len(question_ids)} questions")

    # Check if all pathway questions exist
    all_pathway_questions = []
    for question_ids in pathways.values():
        all_pathway_questions.extend(question_ids)

    missing_questions = set(all_pathway_questions) - set(questions.keys())
    if missing_questions:
        issues.append(f"❌ Missing questions referenced in pathways: {missing_questions}")
    else:
        print("✅ All pathway questions exist")

    if issues:
        print("\n⚠️  Issues found:")
        for issue in issues:
            print(f"   {issue}")
    else:
        print("\n✅ No validation issues found!")

    return tree


def visualize_flow(event_name: str, language: str = 'hi'):
    """Create a simple text-based flow visualization"""

    print_section("Decision Tree Flow Visualization", "=")

    parser = QuestionnaireParser(event_name, language)
    tree = parser.parse()

    if not tree:
        return

    questions = tree.get('questions', {})
    pathways = tree.get('pathways', {})

    print("\n📊 Call Flow:")
    print("\n1. OPENING")
    print("   ↓")
    print("2. Q1: Initial reason question")
    print("   ↓")
    print("   User Response Analysis:")

    q1 = questions.get('q1') or questions.get('Q1')
    if q1 and q1.get('conditions'):
        conditions = q1.get('conditions', {})
        for i, (trigger, next_q) in enumerate(conditions.items(), 1):
            arrow = "└─" if i == len(conditions) else "├─"
            print(f"   {arrow} '{trigger}' → {next_q}")

    print("\n3. Pathway Questions:")
    for pathway_name, question_ids in pathways.items():
        if question_ids and pathway_name != 'clarification':
            print(f"\n   {pathway_name.upper()} PATHWAY:")
            for qid in question_ids:
                if qid in questions:
                    print(f"      → {qid}")

    print("\n4. Q3: Competitive/Alternatives")
    print("5. Q4: Winback Opportunity")
    print("6. CLOSING")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Analyze decision tree from questionnaire')
    parser.add_argument('--event', '-e', default='subscription_cancelled',
                       help='Event name (default: subscription_cancelled)')
    parser.add_argument('--language', '-l', default='hi',
                       help='Language code (default: hi)')
    parser.add_argument('--visualize', '-v', action='store_true',
                       help='Show flow visualization')

    args = parser.parse_args()

    # Analyze
    tree = analyze_questionnaire(args.event, args.language)

    # Visualize if requested
    if args.visualize:
        visualize_flow(args.event, args.language)

    print_section("Analysis Complete", "=")
