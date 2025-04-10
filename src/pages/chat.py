import streamlit as st
import subprocess
import time
import ollama

# ------------------------------
# 1. Server setup (unchanged)
# ------------------------------
def ensure_ollama_server():
    """Checks if the Ollama server is running; if not, starts it in the background."""
    try:
        # On Unix-like systems, we can check 'ollama serve' with pgrep
        subprocess.check_output(["pgrep", "ollama"])
    except subprocess.CalledProcessError:
        st.write("\n")
        st.write("\n")
        st.info("Starting Ollama server...")
        subprocess.Popen(["ollama", "serve"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        time.sleep(2)

def extract_model_name(entry):
    """
    Helper to parse a model entry from `ollama.list()['models']
    """
    if hasattr(entry, 'model') and isinstance(getattr(entry, 'model'), str):
        return entry.model # Access the .model attribute

    # Keep the original dictionary check as a fallback or for other versions
    elif isinstance(entry, dict) and "name" in entry:
        return entry["name"]

    # Keep other original fallbacks if needed
    elif isinstance(entry, str):
        return entry
    elif isinstance(entry, (tuple, list)) and len(entry) > 0:
        return entry[0]
    else:
        return str(entry) # Return string representation as last resort

# ------------------------------
# 2. Generating responses
# ------------------------------
def generate_response(messages, model_name):
    """
    Build a conversation prompt from messages and stream the response.
    Uses a generator function together with st.write_stream so that the
    assistant's message is updated continuously without inserting a new line per token.
    """
    prompt = ""
    for msg in messages:
        if msg["role"] == "user":
            prompt += f"User: {msg['content']}\n"
        else:
            prompt += f"Assistant: {msg['content']}\n"
    prompt += "Assistant:"

    # Define a generator to yield each streaming chunk after replacing newlines with spaces.
    def response_generator():
        for chunk in ollama.generate(model=model_name, prompt=prompt, stream=True):
            if chunk.done:
                break
            # Replace newlines with spaces so text flows on a single line.
            yield chunk.response

    # Use Streamlit's chat_message container and st.write_stream to display a continuously updated response.
    with st.chat_message("assistant"):
        final_response = st.write_stream(response_generator())
    
    return final_response.strip()

# ------------------------------
# 3. Main UI
# ------------------------------
def main():
    st.set_page_config(
        page_title="Ollama Chat Interface",
        layout="centered",
        initial_sidebar_state="expanded"
    )

    # Inject custom CSS for a neat chat UI
    st.markdown(
        """
        <style>
        .main {
            max-width: 800px;
            margin: 0 auto;
        }
        [data-testid="stChatMessage"] {
            border: 1px solid #3f3f3f;
            padding: 1rem;
            border-radius: 0.5rem;
            margin: 0.5rem 0;
        }
        [data-testid="stChatMessage"]:has(div:has-text("User:")) {
            background: #313131;
        }
        [data-testid="stChatMessage"]:has(div:has-text("Assistant:")) {
            background: #1e1e1e;
        }
        .block-container {
            padding-top: 1rem;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    ensure_ollama_server()

    # 3A. Sidebar for model selection
    st.sidebar.title("Model Selection")
    available_models_in_ui = [
        "gemma3:12b",
        "deepseek-r1:8b",
        "llama3.2:latest",
        "llama3.1:latest",
        "mistral:latest"
    ]

    if "selected_model" not in st.session_state:
        st.session_state["selected_model"] = available_models_in_ui[0]

    st.session_state["selected_model"] = st.sidebar.selectbox(
        "Select a model:",
        options=available_models_in_ui,
        index=available_models_in_ui.index(st.session_state["selected_model"])
    )
    model_name = st.session_state["selected_model"]

    # Retrieve local models from Ollama by accessing the 'models' key
    try:
        models_dict = ollama.list()
        local_models = models_dict["models"]
        local_model_names = [extract_model_name(m) for m in local_models]
    except Exception as e:
        st.error(f"Error listing locally available models: {str(e)}")
        local_model_names = []

    # Pull model if not found locally
    if model_name not in local_model_names:
        st.write("\n")
        st.write("\n")
        st.info(f"Model '{model_name}' not found locally. Pulling the model now. "
                "This is only required once and may take a while...")
        try:
            ollama.pull(model=model_name)
            st.success(f"Successfully pulled '{model_name}'.")
        except Exception as e:
            st.error(f"Error pulling model '{model_name}': {str(e)}")

    st.title("Ollama Chat Interface")

    # 3B. Maintain conversation history in session_state
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    # Display chat history using the new chat UI components
    for msg in st.session_state["messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 3C. Chat input remains at the bottom (using st.chat_input)
    user_text = st.chat_input("Type your message...")

    if user_text:
        # Append and display user message
        st.session_state["messages"].append({"role": "user", "content": user_text})
        with st.chat_message("user"):
            st.markdown(user_text)

        # Generate and display assistant response with streaming
        with st.spinner("Thinking..."):
            assistant_reply = generate_response(st.session_state["messages"], model_name)

        # Append assistant's final response to the conversation history
        st.session_state["messages"].append({"role": "assistant", "content": assistant_reply})

if __name__ == "__main__":
    main()
