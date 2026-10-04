import streamlit as st
import os
from langchain_openai import OpenAIEmbeddings
from langchain_postgres import PGVector
from langchain.schema import Document
import numpy as np
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

STATE_PREFIX = "slack_"

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
    {"name": "help", "description": "Get help with any questions or issues", "topic": "Support"},
    {"name": "sports-talk", "description": "Sports discussions, games, and team activities", "topic": "Football, cricket, fitness"},
    {"name": "random", "description": "Random fun conversations and memes", "topic": "Fun, casual chat"},
]

def init_state():
    keys = ["channels", "channel_embeddings", "embeddings_model"]
    for key in keys:
        if f"{STATE_PREFIX}{key}" not in st.session_state:
            st.session_state[f"{STATE_PREFIX}{key}"] = [] if key == "channels" else None

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def fetch_real_slack_channels():
    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return None, "SLACK_BOT_TOKEN not found"
    try:
        client = WebClient(token=token)
        result = client.conversations_list(types="public_channel,private_channel")
        channels = [{"name": ch["name"], "description": ch.get("purpose", {}).get("value", "No description"), "topic": ch.get("topic", {}).get("value", "")} for ch in result["channels"]]
        return channels, None
    except SlackApiError as e:
        return None, f"Slack API Error: {e.response['error']}"

def fetch_slack_channels(use_real_slack=False):
    if use_real_slack:
        channels, error = fetch_real_slack_channels()
        if error:
            return channels, error
    else:
        channels = HARDCODED_CHANNELS

    try:
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            return channels, "Warning: OPENAI_API_KEY not found"

        embeddings_model = OpenAIEmbeddings(openai_api_key=openai_key)
        st.session_state[f"{STATE_PREFIX}embeddings_model"] = embeddings_model
        channel_texts = [f"{ch['name']} {ch['description']} {ch['topic']}" for ch in channels]
        channel_embeddings = embeddings_model.embed_documents(channel_texts)
        st.session_state[f"{STATE_PREFIX}channel_embeddings"] = channel_embeddings

        # Store in vector database
        store_channels_in_db(channels, embeddings_model)

        return channels, None
    except Exception as e:
        return channels, f"Warning: {str(e)}"

def store_channels_in_db(channels, embeddings_model):
    """Store Slack channels in vector database for unified search"""
    try:
        documents = []
        for ch in channels:
            content = f"""Slack Channel: #{ch['name']}
Description: {ch['description']}
Topic: {ch['topic']}

This is a Slack channel for {ch['description']}. Use this channel for discussions about {ch['topic']}."""

            doc = Document(
                page_content=content,
                metadata={
                    "source": f"#{ch['name']}",
                    "type": "slack_channel",
                    "channel_name": ch['name'],
                    "description": ch['description'],
                    "topic": ch['topic']
                }
            )
            documents.append(doc)

        vectorstore = PGVector.from_documents(
            documents=documents,
            embedding=embeddings_model,
            collection_name="slack_channels",
            connection=os.getenv("DATABASE_URL"),
            pre_delete_collection=True
        )

        # Verify storage
        test_results = vectorstore.similarity_search("backend", k=1)
        if test_results:
            st.success(f"✅ Verified: Found '{test_results[0].metadata.get('channel_name')}' in DB")

        return True
    except Exception as e:
        st.error(f"Failed to store in DB: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
        return False

def find_matching_channels(query, channels):
    if st.session_state[f"{STATE_PREFIX}embeddings_model"] and st.session_state[f"{STATE_PREFIX}channel_embeddings"]:
        try:
            query_embedding = st.session_state[f"{STATE_PREFIX}embeddings_model"].embed_query(query)
            similarities = [(channels[i], cosine_similarity(query_embedding, st.session_state[f"{STATE_PREFIX}channel_embeddings"][i])) for i in range(len(channels))]
            similarities.sort(key=lambda x: x[1], reverse=True)
            return [s[0] for s in similarities[:5]]
        except:
            pass

    query_lower = query.lower()
    matches = []
    for channel in channels:
        score = sum(1 for word in query_lower.split() if len(word) > 2 and word in f"{channel['name']} {channel['description']} {channel['topic']}".lower())
        if score > 0:
            matches.append((channel, score))
    matches.sort(key=lambda x: x[1], reverse=True)
    return [m[0] for m in matches[:5]]

def render_connection():
    init_state()

    use_real_slack = st.checkbox("Use Real Slack API", value=False, key="slack_real")

    if use_real_slack:
        st.info("Set SLACK_BOT_TOKEN in .env")

    if st.button("Load Channels", type="primary", key="slack_load"):
        with st.spinner("Loading..."):
            channels, error = fetch_slack_channels(use_real_slack=use_real_slack)
            if error:
                st.error(error)
            else:
                st.session_state[f"{STATE_PREFIX}channels"] = channels
                st.session_state.connected_tools["slack"] = True

                # Add to active collections - CRITICAL
                if "active_collections" not in st.session_state:
                    st.session_state.active_collections = []
                if "slack_channels" not in st.session_state.active_collections:
                    st.session_state.active_collections.append("slack_channels")

                st.success(f"✅ Loaded {len(channels)} channels & indexed to DB")
                st.info(f"Active collections now: {st.session_state.active_collections}")
                st.rerun()

    if st.session_state[f"{STATE_PREFIX}channels"]:
        st.metric("Channels", len(st.session_state[f"{STATE_PREFIX}channels"]))

        # Test DB button
        if st.button("🔍 Test DB Query", key="slack_test_db"):
            try:
                embeddings = OpenAIEmbeddings(openai_api_key=os.getenv("OPENAI_API_KEY"))
                vs = PGVector(
                    embeddings=embeddings,
                    collection_name="slack_channels",
                    connection=os.getenv("DATABASE_URL")
                )
                results = vs.similarity_search("backend developer", k=3)
                st.success(f"✅ Found {len(results)} docs in DB")
                for r in results:
                    st.write(f"#{r.metadata.get('channel_name')} - {r.metadata.get('type')}")
            except Exception as e:
                st.error(f"❌ DB Error: {e}")

        query = st.text_input("Find channel:", placeholder="backend questions?", key="slack_query")

        if query:
            matches = find_matching_channels(query, st.session_state[f"{STATE_PREFIX}channels"])
            if matches:
                for channel in matches[:3]:
                    st.text(f"#{channel['name']} - {channel['description'][:50]}...")

    if "slack" in st.session_state.connected_tools and st.button("Disconnect", key="slack_disconnect"):
        del st.session_state.connected_tools["slack"]
        st.rerun()
