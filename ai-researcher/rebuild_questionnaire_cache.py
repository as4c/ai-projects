#!/usr/bin/env python
"""
Script to rebuild questionnaire caches.
Run this after modifying any questionnaire .txt files.

Usage:
    python rebuild_questionnaire_cache.py                    # Rebuild all
    python rebuild_questionnaire_cache.py subscription_cancelled hi  # Rebuild specific
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_researcher.settings')
import django
django.setup()

from ai_researcher.questionnaire_parser import QuestionnaireParser


def main():
    if len(sys.argv) == 1:
        # Rebuild all caches
        print("=" * 60)
        print("Rebuilding all questionnaire caches...")
        print("=" * 60)

        results = QuestionnaireParser.rebuild_all_caches()

        print("\n" + "=" * 60)
        print("Results:")
        print("=" * 60)

        for key, success in results.items():
            status = "✅ Success" if success else "❌ Failed"
            print(f"  {key}: {status}")

        success_count = sum(1 for v in results.values() if v)
        print(f"\nTotal: {success_count}/{len(results)} successful")

    elif len(sys.argv) == 3:
        # Rebuild specific cache
        event_name = sys.argv[1]
        language = sys.argv[2]

        print(f"Rebuilding cache for {event_name}/{language}...")
        success = QuestionnaireParser.rebuild_cache(event_name, language)

        if success:
            print(f"✅ Successfully rebuilt cache for {event_name}/{language}")
        else:
            print(f"❌ Failed to rebuild cache for {event_name}/{language}")
            sys.exit(1)
    else:
        print("Usage:")
        print("  python rebuild_questionnaire_cache.py                         # Rebuild all")
        print("  python rebuild_questionnaire_cache.py <event_name> <language> # Rebuild specific")
        print("\nExamples:")
        print("  python rebuild_questionnaire_cache.py")
        print("  python rebuild_questionnaire_cache.py subscription_cancelled hi")
        sys.exit(1)


if __name__ == "__main__":
    main()

