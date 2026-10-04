"""
Streamlit UI for Managing Questionnaires
Upload PDF, TXT, or DOCX files containing questionnaires
"""
import streamlit as st
import os
from pathlib import Path
import uuid
from datetime import datetime

# Page config
st.set_page_config(
    page_title="Questionnaire Manager",
    page_icon="📋",
    layout="wide"
)

# Create questionnaires folder if it doesn't exist
QUESTIONNAIRE_FOLDER = Path("questionnaires")
QUESTIONNAIRE_FOLDER.mkdir(exist_ok=True)

st.title("📋 Questionnaire Manager")
st.markdown("Upload questionnaire files (PDF, TXT, DOCX) to create different questionnaire types")

# Sidebar for navigation
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "Choose a page",
    ["Upload Questionnaire", "View Questionnaires", "Manage Questionnaires", "Call Dashboard"]
)

if page == "Upload Questionnaire":
    st.header("Upload New Questionnaire")

    # File uploader
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=['pdf', 'txt', 'docx'],
        help="Upload PDF, TXT, or DOCX file containing your questionnaire"
    )

    if uploaded_file is not None:
        # Get file details
        file_name = uploaded_file.name
        file_type = uploaded_file.type
        file_size = uploaded_file.size

        st.info(f"📄 File: {file_name} | Type: {file_type} | Size: {file_size:,} bytes")

        # Event name/Topic name input (for API mapping) - REQUIRED
        event_name = st.text_input(
            "Event Name / Topic Name *",
            value=file_name.split('.')[0].replace('_', ' ').replace('-', ' ').lower().replace(' ', '_'),
            help="This will be used in API payload as 'event_name' to map to this questionnaire. This is REQUIRED.",
            placeholder="e.g., gyantv_survey, customer_feedback"
        )

        # Questionnaire name input (optional, for display)
        questionnaire_name = st.text_input(
            "Questionnaire Display Name (Optional)",
            value=file_name.split('.')[0].replace('_', ' ').replace('-', ' ').title(),
            help="Give a friendly name for display purposes (optional)"
        )

        # Preview file content
        st.subheader("File Preview")

        try:
            if file_type == "text/plain" or file_name.endswith('.txt'):
                # Read text file
                content = uploaded_file.read().decode('utf-8')
                st.text_area("Content", content, height=300)

            elif file_type == "application/pdf" or file_name.endswith('.pdf'):
                st.info("PDF preview not available. Content will be extracted on save.")

            elif file_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document" or file_name.endswith('.docx'):
                st.info("DOCX preview not available. Content will be extracted on save.")

        except Exception as e:
            st.error(f"Error reading file: {e}")

        # Language selection for source
        source_language = st.selectbox(
            "Source Language",
            options=['en', 'hi'],
            index=0,
            help="Language of the uploaded questionnaire file"
        )

        # Save button
        if st.button("💾 Save Questionnaire", type="primary"):
            if not event_name:
                st.error("⚠️ Event Name / Topic Name is REQUIRED!")
            else:
                try:
                    # Extract text from file
                    file_content = ""
                    uploaded_file.seek(0)  # Reset file pointer
                    if file_type == "text/plain" or file_name.endswith('.txt'):
                        file_content = uploaded_file.read().decode('utf-8')
                    elif file_name.endswith('.docx'):
                        try:
                            import docx
                            from io import BytesIO
                            doc = docx.Document(BytesIO(uploaded_file.getbuffer()))
                            file_content = "\n".join([para.text for para in doc.paragraphs])
                        except ImportError:
                            st.error("python-docx library not installed. Please install it: pip install python-docx")
                            file_content = ""
                        except Exception as e:
                            st.warning(f"Could not extract DOCX content: {e}. Please upload as TXT.")
                            file_content = ""
                    elif file_name.endswith('.pdf'):
                        try:
                            # Try using pdfplumber first (better text extraction)
                            try:
                                import pdfplumber
                                from io import BytesIO
                                with pdfplumber.open(BytesIO(uploaded_file.getbuffer())) as pdf:
                                    text_parts = []
                                    for page in pdf.pages:
                                        text = page.extract_text()
                                        if text:
                                            text_parts.append(text)
                                file_content = "\n\n".join(text_parts)

                                # Clean up spacing issues - remove excessive spaces between words
                                import re
                                # Replace multiple spaces/newlines with single space, but preserve paragraph breaks
                                file_content = re.sub(r' +', ' ', file_content)  # Multiple spaces to single
                                file_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', file_content)  # Multiple newlines to double
                                file_content = file_content.strip()

                            except ImportError:
                                # pdfplumber not installed, try PyPDF2
                                try:
                                    import PyPDF2
                                    from io import BytesIO
                                    pdf_reader = PyPDF2.PdfReader(BytesIO(uploaded_file.getbuffer()))
                                    text_parts = []
                                    for page_num, page in enumerate(pdf_reader.pages):
                                        try:
                                            text_parts.append(page.extract_text())
                                        except Exception as e:
                                            st.warning(f"Could not extract text from page {page_num + 1}: {e}")
                                    file_content = "\n\n".join(text_parts)

                                    # Clean up spacing issues
                                    import re
                                    file_content = re.sub(r' +', ' ', file_content)
                                    file_content = re.sub(r'\n\s*\n\s*\n+', '\n\n', file_content)
                                    file_content = file_content.strip()

                                except ImportError:
                                    st.error("PDF extraction libraries not installed. Please install one: pip install pdfplumber OR pip install PyPDF2")
                                    file_content = ""
                                except Exception as e:
                                    st.error(f"PDF extraction failed: {e}. Please convert to TXT first.")
                                    file_content = ""
                            except Exception as e:
                                st.error(f"PDF extraction failed: {e}. Please convert to TXT first.")
                                file_content = ""
                        except Exception as e:
                            st.error(f"Unexpected error during PDF extraction: {e}. Please convert to TXT first.")
                            file_content = ""

                    if not file_content:
                        st.error("Could not extract text from file. Please ensure the file contains readable text.")
                    else:
                        # Show progress
                        progress_bar = st.progress(0)
                        status_text = st.empty()

                        # Initialize Django to use translation
                        import sys
                        BASE_DIR = Path(__file__).resolve().parent
                        sys.path.insert(0, str(BASE_DIR))
                        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_researcher.settings')
                        import django
                        django.setup()

                        from ai_researcher.questionnaire_translator import translate_questionnaire_to_all_languages
                        from django.conf import settings as django_settings

                        # Translate to all supported languages
                        status_text.text("🔄 Translating questionnaire to all supported languages...")
                        progress_bar.progress(0.2)

                        supported_languages = getattr(django_settings, 'SUPPORTED_LANGUAGES', ['en', 'hi'])
                        # Use translation-specific provider (falls back to DEFAULT_LLM_PROVIDER if not set)
                        translation_provider = getattr(django_settings, 'DEFAULT_TRANSLATION_PROVIDER', None)
                        if not translation_provider:
                            translation_provider = getattr(django_settings, 'DEFAULT_LLM_PROVIDER', 'gemini')
                        translations = translate_questionnaire_to_all_languages(
                            file_content,
                            source_language=source_language,
                            provider=translation_provider
                        )

                        progress_bar.progress(0.8)

                        # Create event_name folder structure
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        safe_name = event_name.replace(' ', '_').replace('-', '_')
                        event_folder = QUESTIONNAIRE_FOLDER / safe_name
                        event_folder.mkdir(exist_ok=True)

                        # Save original file (optional, for reference)
                        file_extension = file_name.split('.')[-1]
                        original_filename = f"original_{timestamp}.{file_extension}"
                        original_path = event_folder / original_filename

                        uploaded_file.seek(0)  # Reset file pointer
                        with open(original_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())

                        # Save translations for each language as {lang}.txt
                        translation_files = {}
                        for lang, translated_text in translations.items():
                            lang_filename = f"{lang}.txt"
                            lang_path = event_folder / lang_filename
                            with open(lang_path, 'w', encoding='utf-8') as f:
                                f.write(translated_text)
                            translation_files[lang] = {
                                'filename': lang_filename,
                                'path': str(lang_path)
                            }

                        # Save metadata in event folder
                        metadata_file = event_folder / "metadata.json"
                        import json
                        metadata = {
                            "questionnaire_name": questionnaire_name or event_name,
                            "event_name": event_name,
                            "original_filename": file_name,
                            "original_file_path": str(original_path),
                            "file_type": file_type,
                            "source_language": source_language,
                            "supported_languages": supported_languages,
                            "translations": translation_files,
                            "created_at": timestamp,
                            "event_folder": str(event_folder)
                        }

                        with open(metadata_file, "w", encoding='utf-8') as f:
                            json.dump(metadata, f, indent=2, ensure_ascii=False)

                        # Build caches for all languages
                        status_text.text("📦 Building caches for faster loading...")
                        try:
                            from ai_researcher.questionnaire_parser import QuestionnaireParser
                            for lang in translations.keys():
                                QuestionnaireParser.rebuild_cache(safe_name, lang)
                            st.success("✅ Caches built successfully!")
                        except Exception as cache_error:
                            st.warning(f"⚠️ Cache building failed (non-critical): {cache_error}")

                        progress_bar.progress(1.0)
                        status_text.text("✅ Translation complete!")

                        st.success(f"✅ Questionnaire saved successfully!")
                        st.info(f"📁 Event Name: **{event_name}**")
                        st.info(f"📝 Display Name: {questionnaire_name or event_name}")

                        # Show translations
                        st.subheader("📋 Translations Generated")
                        for lang, trans_info in translation_files.items():
                            lang_display = {'en': 'English', 'hi': 'Hindi'}.get(lang, lang)
                            st.success(f"✓ {lang_display} ({lang})")

                        st.balloons()

                        # Show preview of translations
                        with st.expander("👀 Preview Translations"):
                            for lang, translated_text in translations.items():
                                lang_display = {'en': 'English', 'hi': 'Hindi'}.get(lang, lang)
                                st.write(f"**{lang_display} ({lang}):**")
                                preview_text = translated_text[:500] + "..." if len(translated_text) > 500 else translated_text
                                st.text_area(f"{lang_display} Translation Preview", preview_text, height=150, key=f"preview_{lang}_{timestamp}")

                except Exception as e:
                    st.error(f"Error saving file: {e}")
                    st.exception(e)

elif page == "View Questionnaires":
    st.header("View Uploaded Questionnaires")

    # List all questionnaires - look for metadata.json in event_name folders
    metadata_files = list(QUESTIONNAIRE_FOLDER.glob("*/metadata.json"))

    if not metadata_files:
        st.info("No questionnaires uploaded yet. Go to 'Upload Questionnaire' to add one.")
    else:
        import json

        for metadata_file in metadata_files:
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                with st.expander(f"📋 {metadata.get('questionnaire_name', metadata['event_name'])} ({metadata['event_name']})"):
                    col1, col2 = st.columns(2)

                    with col1:
                        st.write("**Event Name:**", metadata['event_name'])
                        st.write("**File Type:**", metadata.get('file_type', 'N/A'))
                        st.write("**Created:**", metadata['created_at'])
                        if 'source_language' in metadata:
                            st.write("**Source Language:**", metadata['source_language'])

                    with col2:
                        st.write("**Original File:**", metadata.get('original_filename', 'N/A'))
                        if 'event_folder' in metadata:
                            st.write("**Event Folder:**", Path(metadata['event_folder']).name)
                        if 'supported_languages' in metadata:
                            st.write("**Languages:**", ", ".join(metadata['supported_languages']))

                    # Show translations if available
                    if 'translations' in metadata and metadata['translations']:
                        st.subheader("🌐 Available Translations")
                        translation_tabs = st.tabs([lang.upper() for lang in metadata.get('supported_languages', ['en', 'hi'])])

                        for idx, lang in enumerate(metadata.get('supported_languages', ['en', 'hi'])):
                            with translation_tabs[idx]:
                                if lang in metadata['translations']:
                                    trans_file = Path(metadata['translations'][lang]['path'])
                                    if trans_file.exists():
                                        with open(trans_file, 'r', encoding='utf-8') as f:
                                            content = f.read()
                                        lang_display = {'en': 'English', 'hi': 'Hindi'}.get(lang, lang)
                                        st.text_area(f"{lang_display} Translation", content, height=300, key=f"trans_{metadata['event_name']}_{lang}")
                                    else:
                                        st.warning(f"Translation file not found: {trans_file}")
                                else:
                                    st.info(f"No translation available for {lang}")

                    # Show original file content if no translations
                    elif 'original_file_path' in metadata:
                        file_path = Path(metadata['original_file_path'])
                        if file_path.exists():
                            if file_path.suffix == '.txt' or file_path.suffix == '':
                                with open(file_path, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                st.text_area("Content", content, height=200, key=f"content_{metadata['event_name']}")

            except Exception as e:
                st.error(f"Error loading {metadata_file}: {e}")

elif page == "Manage Questionnaires":
    st.header("Manage Questionnaires")

    # List all questionnaires with delete option
    metadata_files = list(QUESTIONNAIRE_FOLDER.glob("*_metadata.json"))

    if not metadata_files:
        st.info("No questionnaires to manage.")
    else:
        import json

        for metadata_file in metadata_files:
            try:
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)

                col1, col2, col3 = st.columns([3, 1, 1])

                with col1:
                    st.write(f"**{metadata['questionnaire_name']}**")
                    st.caption(f"Event: {metadata['event_name']} | Created: {metadata['created_at']}")

                with col2:
                    if st.button("🗑️ Delete", key=f"delete_{metadata['event_name']}"):
                        # Delete entire event folder
                        event_folder = Path(metadata.get('event_folder', QUESTIONNAIRE_FOLDER / metadata['event_name']))
                        if event_folder.exists():
                            import shutil
                            shutil.rmtree(event_folder)
                            st.success("Deleted!")
                            st.rerun()
                        else:
                            st.error("Event folder not found!")

                with col3:
                    if st.button("📥 Download", key=f"download_{metadata['event_name']}"):
                        # Download the first available translation or original
                        event_folder = Path(metadata.get('event_folder', QUESTIONNAIRE_FOLDER / metadata['event_name']))
                        if 'translations' in metadata and metadata['translations']:
                            # Download first translation
                            first_lang = list(metadata['translations'].keys())[0]
                            trans_path = Path(metadata['translations'][first_lang]['path'])
                            if trans_path.exists():
                                with open(trans_path, "rb") as f:
                                    st.download_button(
                                        f"Download {first_lang.upper()}",
                                        f.read(),
                                        file_name=f"{metadata['event_name']}_{first_lang}.txt",
                                        key=f"dl_{metadata['event_name']}"
                                    )
                        elif 'original_file_path' in metadata:
                            orig_path = Path(metadata['original_file_path'])
                            if orig_path.exists():
                                with open(orig_path, "rb") as f:
                                    st.download_button(
                                        "Download Original",
                                        f.read(),
                                        file_name=metadata.get('original_filename', 'questionnaire.txt'),
                                        key=f"dl_{metadata['event_name']}"
                                    )

                st.divider()

            except Exception as e:
                st.error(f"Error: {e}")

elif page == "Call Dashboard":
    st.header("📞 Call Dashboard")
    st.markdown("View all call data including user information, transcripts, and insights")

    # Setup paths
    import sys
    from pathlib import Path

    # Try to import Django settings
    try:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_researcher.settings')
        import django
        django.setup()
        from django.conf import settings

        media_root = Path(settings.MEDIA_ROOT)
        call_data_dir = media_root / 'call_data'

        # Create tabs
        tab1, tab2, tab3 = st.tabs(["📊 All Calls", "🔍 Search Calls", "📈 Analytics"])

        with tab1:
            st.subheader("All Call Records")

            # List all call data files
            call_data_files = sorted(call_data_dir.glob("call_data_*.txt"), reverse=True) if call_data_dir.exists() else []

            if not call_data_files:
                st.info("No call records found. Make some calls to see data here.")
            else:
                st.success(f"Found {len(call_data_files)} call record(s)")

                # Display calls in expandable sections
                for idx, call_file in enumerate(call_data_files):
                    try:
                        with open(call_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        # Extract key info from file
                        lines = content.split('\n')
                        call_info = {}

                        for line in lines:
                            if ':' in line and not line.startswith('=') and not line.startswith('-'):
                                key, value = line.split(':', 1)
                                key = key.strip()
                                value = value.strip()
                                if key and value != 'N/A':
                                    call_info[key] = value

                        # Display in expandable
                        call_name = call_info.get('Name', 'Unknown')
                        call_date = call_info.get('Call Created On', 'Unknown Date')
                        with st.expander(f"📞 Call #{idx+1}: {call_name} - {call_date}"):
                            col1, col2 = st.columns(2)

                            with col1:
                                st.write("**User Info**")
                                st.write(f"Name: {call_info.get('Name', 'N/A')}")
                                st.write(f"Phone: {call_info.get('Phone Number', 'N/A')}")
                                st.write(f"Gender: {call_info.get('Gender', 'N/A')}")
                                st.write(f"Age: {call_info.get('Age', 'N/A')}")
                                st.write(f"Event: {call_info.get('Event Name', 'N/A')}")

                            with col2:
                                st.write("**Call Info**")
                                st.write(f"Call SID: {call_info.get('Call SID', 'N/A')}")
                                st.write(f"Duration: {call_info.get('Duration', 'N/A')} seconds")
                                st.write(f"Status: {call_info.get('Status', 'N/A')}")
                                rec_url = call_info.get('Recording URL', 'N/A')
                                if len(rec_url) > 50:
                                    rec_url = rec_url[:50] + "..."
                                st.write(f"Recording URL: {rec_url}")

                            # Show transcript
                            if 'TRANSCRIPT' in content:
                                transcript_start = content.find('TRANSCRIPT')
                                insights_start = content.find('LLM GENERATED INSIGHTS')
                                transcript_section = content[transcript_start:insights_start] if insights_start > transcript_start else content[transcript_start:]
                                st.write("**Transcript**")
                                st.text_area("Call Transcript", transcript_section, height=200, key=f"transcript_{idx}")

                            # Show insights
                            if 'LLM GENERATED INSIGHTS' in content:
                                insights_start = content.find('LLM GENERATED INSIGHTS')
                                insights_section = content[insights_start:]
                                st.write("**LLM Insights**")
                                st.text_area("LLM Generated Insights", insights_section, height=150, key=f"insights_{idx}")

                            # Download button
                            st.download_button(
                                "📥 Download Full Call Data",
                                content,
                                file_name=call_file.name,
                                key=f"download_{idx}"
                            )

                    except Exception as e:
                        st.error(f"Error reading {call_file.name}: {e}")

        with tab2:
            st.subheader("Search Calls")

            search_term = st.text_input("Search by name, phone, or event name")

            if search_term:
                matching_files = []
                for call_file in call_data_files:
                    try:
                        with open(call_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if search_term.lower() in content.lower():
                                matching_files.append((call_file, content))
                    except:
                        pass

                if matching_files:
                    st.success(f"Found {len(matching_files)} matching call(s)")
                    for call_file, content in matching_files:
                        st.text_area(f"Match: {call_file.name}", content[:500] + "...", height=150)
                else:
                    st.info("No matching calls found")

        with tab3:
            st.subheader("Analytics")

            if call_data_files:
                # Basic statistics
                total_calls = len(call_data_files)
                st.metric("Total Calls", total_calls)

                # Extract data for analytics
                names = []
                genders = []
                events = []
                durations = []

                for call_file in call_data_files:
                    try:
                        with open(call_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            for line in content.split('\n'):
                                if 'Name:' in line and 'N/A' not in line:
                                    names.append(line.split('Name:')[1].strip())
                                if 'Gender:' in line and 'N/A' not in line:
                                    genders.append(line.split('Gender:')[1].strip())
                                if 'Event Name:' in line and 'N/A' not in line:
                                    events.append(line.split('Event Name:')[1].strip())
                                if 'Duration:' in line and 'seconds' in line:
                                    try:
                                        dur = int(line.split('Duration:')[1].split('seconds')[0].strip())
                                        durations.append(dur)
                                    except:
                                        pass
                    except:
                        pass

                col1, col2, col3 = st.columns(3)
                with col1:
                    if genders:
                        gender_counts = {}
                        for g in genders:
                            gender_counts[g] = gender_counts.get(g, 0) + 1
                        st.write("**Gender Distribution**")
                        st.bar_chart(gender_counts)

                with col2:
                    if events:
                        event_counts = {}
                        for e in events:
                            event_counts[e] = event_counts.get(e, 0) + 1
                        st.write("**Event Distribution**")
                        st.bar_chart(event_counts)

                with col3:
                    if durations:
                        avg_duration = sum(durations) / len(durations)
                        st.metric("Avg Call Duration", f"{avg_duration:.1f} seconds")
            else:
                st.info("No call data available for analytics")

    except Exception as e:
        st.error(f"Error loading Django settings: {e}")
        st.info("Make sure Django is properly configured. You can still view call data files manually.")

        # Fallback: show files in call_data directory if it exists
        call_data_dir = Path("media/call_data")
        if call_data_dir.exists():
            files = list(call_data_dir.glob("*.txt"))
            st.write(f"Found {len(files)} call data file(s)")
            for f in files:
                st.text(f.name)

