import openai
import gradio as gr
from dotenv import load_dotenv
import os
import threading
import queue
from typing import override
from config import (
    ASSISTANT_MODEL, AUDIO_MODEL, AUDIO_VOICE, CHARACTER_DELAY, INSTRUCTIONS_FILE_PATH
)

# OpenAI: API key
load_dotenv()
openai.key = os.getenv('OPENAI_API_KEY')

# Load instructions from a file
def load_instructions(file_path):
    """Load instructions from a specified file path."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

instructions = load_instructions(INSTRUCTIONS_FILE_PATH)

# OpenAI: Create an assistant
assistant = openai.beta.assistants.create(
    name="Game Master",
    instructions=instructions,
    tools=[{"type": "code_interpreter"}],
    model=ASSISTANT_MODEL
)

# OpenAI: Create new thread
thread = openai.beta.threads.create()

# This is your queue where data from the OpenAI API will be stored.
data_queue = queue.Queue()
streaming_active = False  # This will control the while loop in handle_user_input

class EventHandler(openai.AssistantEventHandler):
    """
    This is your event handler that will receive data from the OpenAI API and put it into the queue.
    """
    @override
    def on_text_delta(self, delta, snapshot):
        data_queue.put(delta.value)
    
    def end_of_stream(self):
        global streaming_active
        streaming_active = False

def openai_streaming_thread(thread_id, assistant_id, event_handler):
    """
    Function to handle OpenAI streaming in a separate thread.
    """
    global streaming_active
    streaming_active = True  # Explicitly set it to True when starting the stream

    def stream():
        with openai.beta.threads.runs.create_and_stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()
        event_handler.end_of_stream()
    
    # Start the streaming in a new thread
    threading.Thread(target=stream).start()

def generate_responses(message, history):
    """
    This function is called by Gradio and yields responses as they are received.
    """
    # Send the user message to the OpenAI API
    openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=message,
        )

    # Start the OpenAI stream in a separate thread
    openai_streaming_thread(thread.id, assistant.id, EventHandler())

    accumulated_response = ""  # Initialize an empty string to accumulate responses

    while streaming_active or not data_queue.empty():
        if not data_queue.empty():
            text = data_queue.get()
            accumulated_response += text
        else:
            yield accumulated_response

gr.ChatInterface(generate_responses).launch()