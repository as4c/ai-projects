"""
Call Data Storage Module
Handles saving call data to files (and can be extended to database)
"""
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
from django.conf import settings


class CallDataStorage:
    """
    Handles storage of call data
    Currently saves to TXT files, but can be extended to save to database
    """

    def __init__(self):
        """Initialize storage directories"""
        self.media_root = Path(settings.MEDIA_ROOT)
        self.media_root.mkdir(parents=True, exist_ok=True)
        self.call_data_dir = self.media_root / 'call_data'
        self.call_data_dir.mkdir(exist_ok=True)

    def save_call_data(self, call_data: Dict) -> Optional[Path]:
        """
        Save call data to storage (file or database)

        Args:
            call_data: Dictionary containing all call information:
                - user_name: str
                - phone_number: str
                - user_gender: str
                - user_age: str
                - event_name: str
                - call_sid: str
                - recording_sid: str
                - call_created_on: str (ISO format timestamp)
                - duration: str (seconds)
                - status: str
                - recording_url: str
                - recording_file: str
                - recording_path: str
                - transcript: str (formatted or raw)
                - user_responses: dict (optional)
                - insights: str (optional, LLM generated)

        Returns:
            Path to saved file, or None if save failed
        """
        try:
            # Save to file (current implementation)
            return self._save_to_file(call_data)

            # Future: Uncomment to add database support
            # return self._save_to_database(call_data)

        except Exception as e:
            print(f"Error saving call data: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _save_to_file(self, call_data: Dict) -> Optional[Path]:
        """
        Save call data to TXT file

        Args:
            call_data: Dictionary with call data

        Returns:
            Path to saved file
        """
        try:
            recording_sid = call_data.get('recording_sid', 'unknown')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            call_data_filename = f"call_data_{recording_sid}_{timestamp}.txt"
            call_data_file_path = self.call_data_dir / call_data_filename

            with open(call_data_file_path, 'w', encoding='utf-8') as f:
                f.write("=" * 70 + "\n")
                f.write("CALL DATA SUMMARY\n")
                f.write("=" * 70 + "\n\n")

                # User Information
                f.write("USER INFORMATION\n")
                f.write("-" * 70 + "\n")
                f.write(f"Name: {call_data.get('user_name', 'N/A')}\n")
                f.write(f"Phone Number: {call_data.get('phone_number', 'N/A')}\n")
                f.write(f"Gender: {call_data.get('user_gender', 'N/A')}\n")
                f.write(f"Age: {call_data.get('user_age', 'N/A')}\n")
                f.write(f"Event Name: {call_data.get('event_name', 'N/A')}\n")
                f.write(f"\n")

                # Call Information
                f.write("CALL INFORMATION\n")
                f.write("-" * 70 + "\n")
                f.write(f"Call SID: {call_data.get('call_sid', 'N/A')}\n")
                f.write(f"Recording SID: {call_data.get('recording_sid', 'N/A')}\n")
                f.write(f"Call Created On: {call_data.get('call_created_on', datetime.now().isoformat())}\n")
                f.write(f"Duration: {call_data.get('duration', 'N/A')} seconds\n")
                f.write(f"Status: {call_data.get('status', 'N/A')}\n")
                f.write(f"\n")

                # Recording Information
                f.write("RECORDING INFORMATION\n")
                f.write("-" * 70 + "\n")
                f.write(f"Recording URL: {call_data.get('recording_url', 'N/A')}\n")
                f.write(f"Recording File: {call_data.get('recording_file', 'N/A')}\n")
                f.write(f"Recording Path: {call_data.get('recording_path', 'N/A')}\n")
                f.write(f"\n")

                # Transcript
                f.write("TRANSCRIPT\n")
                f.write("-" * 70 + "\n")
                transcript = call_data.get('transcript', '')
                if transcript:
                    f.write(f"{transcript}\n")
                else:
                    f.write("Transcript not available\n")
                f.write(f"\n")

                # User Responses Summary
                user_responses = call_data.get('user_responses', {})
                if user_responses:
                    f.write("USER RESPONSES SUMMARY\n")
                    f.write("-" * 70 + "\n")
                    for key, value in user_responses.items():
                        f.write(f"{key}: {value}\n")
                    f.write(f"\n")

                # LLM Insights
                f.write("LLM GENERATED INSIGHTS\n")
                f.write("-" * 70 + "\n")
                insights = call_data.get('insights', '')
                if insights:
                    f.write(f"{insights}\n")
                else:
                    f.write("Insights not available\n")
                f.write(f"\n")

                f.write("=" * 70 + "\n")
                f.write(f"Generated on: {datetime.now().isoformat()}\n")
                f.write("=" * 70 + "\n")

            print(f"Call data saved to: {call_data_file_path}")
            return call_data_file_path

        except Exception as e:
            print(f"Error saving call data to file: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _save_to_database(self, call_data: Dict) -> Optional[int]:
        """
        Save call data to database (for future implementation)

        Args:
            call_data: Dictionary with call data

        Returns:
            Database record ID, or None if save failed

        Example implementation:
            from .models import CallRecord

            call_record = CallRecord.objects.create(
                user_name=call_data.get('user_name'),
                phone_number=call_data.get('phone_number'),
                user_gender=call_data.get('user_gender'),
                user_age=call_data.get('user_age'),
                event_name=call_data.get('event_name'),
                call_sid=call_data.get('call_sid'),
                recording_sid=call_data.get('recording_sid'),
                call_created_on=call_data.get('call_created_on'),
                duration=call_data.get('duration'),
                status=call_data.get('status'),
                recording_url=call_data.get('recording_url'),
                recording_file=call_data.get('recording_file'),
                recording_path=call_data.get('recording_path'),
                transcript=call_data.get('transcript'),
                user_responses=call_data.get('user_responses'),
                insights=call_data.get('insights')
            )
            return call_record.id
        """
        # TODO: Implement database storage
        # Uncomment and modify the example above when ready
        pass


# Convenience function for easy usage
def save_call_data(call_data: Dict) -> Optional[Path]:
    """
    Convenience function to save call data

    Args:
        call_data: Dictionary containing all call information

    Returns:
        Path to saved file, or None if save failed

    Example:
        call_data = {
            'user_name': 'John Doe',
            'phone_number': '+1234567890',
            'user_gender': 'male',
            'user_age': '30',
            'event_name': 'gyantv_survey',
            'call_sid': 'CAxxx',
            'recording_sid': 'RExxx',
            'call_created_on': '2024-01-15T10:30:00Z',
            'duration': '120',
            'status': 'completed',
            'recording_url': 'https://...',
            'recording_file': 'recording.mp3',
            'recording_path': '/path/to/recording.mp3',
            'transcript': 'Agent: Hello...',
            'user_responses': {'q1': 'answer1'},
            'insights': 'User is satisfied...'
        }
        file_path = save_call_data(call_data)
    """
    storage = CallDataStorage()
    return storage.save_call_data(call_data)

