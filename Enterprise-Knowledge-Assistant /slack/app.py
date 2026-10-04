import streamlit as st
import os
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
import numpy as np
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

load_dotenv()

# Initialize session state
if "channels" not in st.session_state:
    st.session_state.channels = []
if "channel_embeddings" not in st.session_state:
    st.session_state.channel_embeddings = None
if "embeddings_model" not in st.session_state:
    st.session_state.embeddings_model = None

# Hardcoded channel list
HARDCODED_CHANNELS = [
    {"name": "backend", "description": "Backend development, APIs, databases, and server-side code", "topic": "Java, Python, Node.js"},
    {"name": "frontend", "description": "Frontend development, UI/UX, React, and client-side code", "topic": "React, Vue, CSS"},
    {"name": "database", "description": "Database design, queries, schema, PostgreSQL, MySQL", "topic": "SQL, NoSQL, migrations"},
    {"name": "devops", "description": "DevOps, CI/CD, deployment, infrastructure, Docker, Kubernetes", "topic": "AWS, deployment"},
    {"name": "general", "description": "General discussions and announcements", "topic": "Team updates"},
    {"name": "engineering", "description": "Engineering team discussions, architecture, and technical decisions", "topic": "Tech discussions"},
    {"name": "product", "description": "Product features, requirements, and roadmap discussions", "topic": "Product planning"},
    {"name": "design", "description": "Design discussions, mockups, and UI/UX feedback", "topic": "Figma, design system"},
    {"name": "qa-testing", "description": "Quality assurance, testing, and bug reports", "topic": "Testing, bugs"},
    {"name": "help", "description": "Get help with any questions or issues", "topic": "Support"}
]

def cosine_similarity(a, b):
    """Calculate cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def fetch_real_slack_channels():
    """Fetch real Slack channels using Slack API."""
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return None, "SLACK_BOT_TOKEN not found in .env file"

    try:
        client = WebClient(token=token)
        result = client.conversations_list(types="public_channel,private_channel")

        channels = []
        for channel in result["channels"]:
            channels.append({
                "name": channel["name"],
                "description": channel.get("purpose", {}).get("value", "No description"),
                "topic": channel.get("topic", {}).get("value", "")
            })

        return channels, None
    except SlackApiError as e:
        return None, f"Slack API Error: {e.response['error']}"

def fetch_slack_channels(use_real_slack=False):
    """Return Slack channels (real or hardcoded) and create embeddings."""
    # Fetch channels
    if use_real_slack:
        channels, error = fetch_real_slack_channels()
        if error:
            return None, error
    else:
        channels = HARDCODED_CHANNELS

    # Create embeddings for channels
    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return channels, "Warning: OPENAI_API_KEY not found. Using keyword matching."

        embeddings_model = OpenAIEmbeddings(openai_api_key=openai_key)
        st.session_state.embeddings_model = embeddings_model

        # Create text representation of each channel
        channel_texts = [
            f"{ch['name']} {ch['description']} {ch['topic']}"
            for ch in channels
        ]

        # Generate embeddings
        channel_embeddings = embeddings_model.embed_documents(channel_texts)
        st.session_state.channel_embeddings = channel_embeddings

        return channels, None
    except Exception as e:
        return channels, f"Warning: Could not create embeddings: {str(e)}"

def find_matching_channels(query, channels):
    """Find channels matching the query using embeddings."""
    # Use embedding-based search if available
    if st.session_state.embeddings_model and st.session_state.channel_embeddings:
        try:
            # Generate query embedding
            query_embedding = st.session_state.embeddings_model.embed_query(query)

            # Calculate similarity scores
            similarities = []
            for i, channel in enumerate(channels):
                channel_embedding = st.session_state.channel_embeddings[i]
                similarity = cosine_similarity(query_embedding, channel_embedding)
                similarities.append((channel, similarity))

            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in similarities[:5]]
        except Exception as e:
            st.warning(f"Embedding search failed: {str(e)}. Using keyword matching.")

    # Fallback to keyword matching
    query_lower = query.lower()
    matches = []

    for channel in channels:
        score = 0
        channel_text = f"{channel['name']} {channel['description']} {channel['topic']}".lower()

        for word in query_lower.split():
            if len(word) > 2 and word in channel_text:
                score += 1

        if score > 0:
            matches.append((channel, score))

    matches.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matches[:5]]

def main():
    st.set_page_config(page_title="Slack Channel Helper", page_icon="💬")

    st.title("💬 Slack Channel Helper")
    st.markdown("Find the right Slack channel for your questions")

    # Sidebar
    with st.sidebar:
        st.header("Setup")

        # Option to choose between real and hardcoded channels
        use_real_slack = st.checkbox("Use Real Slack API", value=False)

        if use_real_slack:
            st.info("Make sure SLACK_BOT_TOKEN is set in .env")

        if st.button("🔄 Fetch Slack Channels", type="primary"):
            with st.spinner("Fetching channels..."):
                channels, error = fetch_slack_channels(use_real_slack=use_real_slack)

                if error:
                    st.error(error)
                    if use_real_slack:
                        st.info("Make sure you have:\n1. SLACK_BOT_TOKEN in .env\n2. Bot has channels:read scope\n3. Bot is installed to workspace")
                else:
                    st.session_state.channels = channels
                    source = "real Slack" if use_real_slack else "hardcoded"
                    st.success(f"✅ Loaded {len(channels)} {source} channels!")

        if st.session_state.channels:
            st.metric("Channels Loaded", len(st.session_state.channels))

    # Main area
    if not st.session_state.channels:
        st.info("👈 Click 'Fetch Slack Channels' in the sidebar to get started")

        st.markdown("""
        ### How to use:
        1. Click the button in sidebar to load channels
        2. Type your question below
        3. Get channel recommendations

        ### Example questions:
        - "Where should I post backend questions?"
        - "Which channel for database issues?"
        - "Where to ask about frontend?"
        """)
    else:
        st.subheader("Ask where to post your question")

        query = st.text_input(
            "Your question:",
            placeholder="e.g., Where should I post backend related queries?"
        )

        if query:
            matches = find_matching_channels(query, st.session_state.channels)

            if matches:
                st.success(f"Found {len(matches)} matching channels:")

                for channel in matches:
                    with st.container():
                        st.markdown(f"### #{channel['name']}")
                        st.markdown(f"**Description:** {channel['description']}")
                        if channel['topic']:
                            st.markdown(f"**Topic:** {channel['topic']}")
                        st.divider()
            else:
                st.warning("No matching channels found. Try different keywords.")

if __name__ == "__main__":
    main()
