import os
import time
import streamlit as st
from dotenv import load_dotenv
from langchain.prompts import PromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationalRetrievalChain
from langchain.chat_models import ChatOpenAI
from embeddings import load_embeddings_offline  # Import the embeddings logic
from htmlTemplates import css, bot_template, user_template  # Import CSS and HTML templates

# Load environment variables from the .env file
load_dotenv()

# Retrieve the OpenAI API key from environment variables
openai_api_key = os.getenv("OPENAI_API_KEY")

# Ensure that the OpenAI API key is set
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY not found in environment variables.")

# Define the prompt template for conversation
custom_template = """Given the following conversation and a follow-up question, rephrase the follow-up question to be a standalone question, in its original language.
Chat History:
{chat_history}
Follow Up Input: {question}
Standalone question: """

CUSTOM_QUESTION_PROMPT = PromptTemplate.from_template(custom_template)

# Function to create a conversation chain using the preloaded vectorstore
def get_conversation_chain(vectorstore):
    # Initialize the language model
    llm = ChatOpenAI(
        temperature=0.2,
        openai_api_key=openai_api_key,
        model_name="gpt-3.5-turbo"
    )
    
    # Use ConversationBufferMemory to keep track of the chat history
    memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True, output_key='answer')

    # Create the conversation chain
    conversation_chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=vectorstore.as_retriever(),
        condense_question_prompt=CUSTOM_QUESTION_PROMPT,
        memory=memory
    )
    return conversation_chain

# Function to simulate typing word by word
def simulate_typing_response(message_content, delay=0.1):
    dynamic_area = st.empty()
    full_message = ""
    words = message_content.split()

    # Loop through each word, adding it to the output one by one
    for word in words:
        full_message += word + " "
        dynamic_area.markdown(bot_template.replace("{{MSG}}", full_message), unsafe_allow_html=True)
        time.sleep(delay)

# Function to handle user question and generate a response
def handle_question(question):
    if st.session_state.conversation:
        response = st.session_state.conversation({'question': question})
        st.session_state.chat_history.append({'role': 'user', 'content': question})
        st.session_state.chat_history.append({'role': 'bot', 'content': response['answer']})

        # Only display the latest user question and bot response
        st.write(user_template.replace("{{MSG}}", question), unsafe_allow_html=True)
        simulate_typing_response(response['answer'])
    else:
        st.write("Embeddings not loaded. Please check the FAISS index path.")

# Display memory in the sidebar with buttons for each previous prompt
def display_memory_in_sidebar():
    st.sidebar.header("Conversation History")
    
    # Display the chat history with expanders
    if "chat_history" in st.session_state and st.session_state.chat_history:
        for i in range(0, len(st.session_state.chat_history), 2):
            user_msg = st.session_state.chat_history[i]['content']
            bot_msg = st.session_state.chat_history[i+1]['content'] if i+1 < len(st.session_state.chat_history) else "No response yet"
            with st.sidebar.expander(f"User: {user_msg}"):
                st.write(f"Bot: {bot_msg}")

def main():
    # Page configuration
    st.set_page_config(page_title="Chat with Embeddings", page_icon=":books:")
    st.write(css, unsafe_allow_html=True)  # Use CSS from the external file

    # Only load FAISS embeddings once if not already loaded in the session
    if "vectorstore" not in st.session_state:
        faiss_index_path = "faiss_index"
        try:
            st.session_state.vectorstore = load_embeddings_offline(faiss_index_path)
            st.session_state.conversation = get_conversation_chain(st.session_state.vectorstore)
            st.session_state.chat_history = []  # Initialize chat history if not present
            st.success("Embeddings successfully loaded offline!")
        except Exception as e:
            st.error(f"Failed to load embeddings: {e}")
            st.session_state.conversation = None

    st.header("Chat with Pre-Computed Embeddings :books:")

    # Input field for user questions
    question = st.text_input("Ask a question:")
    if question:
        handle_question(question)

    # Display the conversation history in the sidebar
    display_memory_in_sidebar()

if __name__ == '__main__':
    main()
