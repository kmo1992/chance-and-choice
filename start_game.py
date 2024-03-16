# main.py

import asyncio
import os
import tempfile

import aioconsole
from dotenv import load_dotenv
import openai
import pygame
from config import (ASSISTANT_MODEL, AUDIO_MODEL, AUDIO_VOICE, IMAGE_MODEL, IMAGE_SIZE, CHARACTER_DELAY, INSTRUCTIONS_FILE_PATH)
from typing_extensions import override
from openai import AssistantEventHandler

# Load environment variables and configure the OpenAI API key
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Pygame Mixer for MP3 playback
pygame.mixer.init()

# Load instructions from a file
def load_instructions(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
    
instructions = load_instructions(INSTRUCTIONS_FILE_PATH)

assistant = openai.beta.assistants.create(
    name="Game Master",
    instructions=instructions,
    tools=[{"type": "code_interpreter"}],
    model=ASSISTANT_MODEL
)

thread = openai.beta.threads.create()

async def play_mp3(audio_file_path):
    """Asynchronously play an MP3 audio file without blocking."""
    try:
        pygame.mixer.music.load(audio_file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(1)  # Check every second if the audio is still playing
    except Exception as e:
        print(f"Error playing audio: {e}")

async def type_text(text):
    """Simulate typing out text one character at a time."""
    for char in text:
        print(char, end='', flush=True)  # Print characters without newline, flushing output immediately.
        await asyncio.sleep(CHARACTER_DELAY)  # Adjust delay to match desired typing speed.

async def generate_and_play_audio(response_text):
    """Generate audio from the response text and play it."""
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as tmpfile:
            with openai.audio.speech.with_streaming_response.create(
                model=AUDIO_MODEL,
                voice=AUDIO_VOICE,
                input=response_text
            ) as response:
                response.stream_to_file(tmpfile.name)

            # Create tasks for typing out text and playing audio
            typing_task = asyncio.create_task(type_text(response_text))
            play_audio_task = asyncio.create_task(play_mp3(tmpfile.name))

            # Wait for both tasks to complete
            await typing_task
            await play_audio_task
    except Exception as e:
        print(f"Error generating or playing audio: {e}")

async def generate_and_display_image(response_text):
    """Generate an image based on the response text and display its URL."""
    try:
        hook_image_response = openai.images.generate(
            model=IMAGE_MODEL,
            prompt=response_text,
            n=1,
            size=IMAGE_SIZE
        )
        image_url = hook_image_response.data[0].url
        print(f'Scene URL: {image_url}\n')
    except Exception as e:
        print(f"Error generating image: {e}")

# First, we create a EventHandler class to define
# how we want to handle the events in the response stream.
 
class EventHandler(AssistantEventHandler):
  def __init__(self):
    super().__init__()
    self.text_buffer = ""
    self.audio_queue = asyncio.Queue()

  @override
  def on_text_created(self, text) -> None:
    print(f"\nassistant > ", end="", flush=True)
      
  @override
  def on_text_delta(self, delta, snapshot):
    # Accumulate text in the buffer
    self.text_buffer += delta.value

    # Process complete paragraphs
    while '\n\n' in self.text_buffer:
        # Find the first paragraph break
        break_index = self.text_buffer.index('\n\n') + 2
        # Extract the paragraph
        paragraph = self.text_buffer[:break_index]
        # Process the paragraph
        self.audio_queue.put_nowait(paragraph)
        # Remove the processed paragraph from the buffer
        self.text_buffer = self.text_buffer[break_index:]

  async def audio_playback_worker(self):
    while True:      
        try:  
            text_to_speak = await self.audio_queue.get()
            await generate_and_play_audio(text_to_speak)
            self.audio_queue.task_done()
        except asyncio.QueueEmpty:
            await asyncio.sleep(0.1)
        except Exception as e:
            print(f"Error in audio playback worker: {e}")
            
  def end_of_stream(self):
    # Handle any remaining data in the buffer as the last paragraph
    if self.text_buffer.strip():
        self.audio_queue.put_nowait(self.text_buffer)
        self.text_buffer = ""  # Clear the buffer

  def on_tool_call_created(self, tool_call):
    print(f"\nassistant > {tool_call.type}\n", flush=True)
  
  def on_tool_call_delta(self, delta, snapshot):
    if delta.type == 'code_interpreter':
      if delta.code_interpreter.input:
        print(delta.code_interpreter.input, end="", flush=True)
      if delta.code_interpreter.outputs:
        print(f"\n\noutput >", flush=True)
        for output in delta.code_interpreter.outputs:
          if output.type == "logs":
            print(f"\n{output.logs}", flush=True)

async def generate_and_play_response(user_input):
    """Generate a response based on user input, then concurrently play audio and generate an image."""
    event_handler = EventHandler()
    worker_task = asyncio.create_task(event_handler.audio_playback_worker())

    try:
        message = openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # This is a simplified adaptation. Your actual implementation
        # will need to consider asynchronous execution and how you manage
        # the state and output of the stream.
        with openai.beta.threads.runs.create_and_stream(
            thread_id=thread.id,
            assistant_id=assistant.id,
            event_handler=event_handler,
        ) as stream:
            stream.until_done()
        
        event_handler.end_of_stream()

        # Retrieve all the messages added after our last user message
        messages = openai.beta.threads.messages.list(
            thread_id=thread.id, order="asc", after=message.id
        )

        # Concatenate all messages where role == "assistant"
        concatenated_messages = " ".join(
            message.content[0].text.value
            for message in messages.data
            if message.role == "assistant"
        )

        # # Create tasks for audio and image generation to run concurrently
        # audio_task = asyncio.create_task(generate_and_play_audio(concatenated_messages))
        # image_task = asyncio.create_task(generate_and_display_image(concatenated_messages))

        # # Wait for the image task to complete first to ensure its output is handled as soon as it's ready
        # await image_task
        # # Then wait for the audio task, ensuring it also completes
        # await audio_task

         # Wait until the audio queue is empty before exiting
        await event_handler.audio_queue.join()
    except Exception as e:
        print(f"Error in generating and playing response: {e}")
    finally:
       worker_task.cancel()

async def main_game_loop():
    """Main game loop for asynchronously handling user actions."""

    while True:
        user_input = await aioconsole.ainput("\n\nuser (type 'quit' to exit) > ")
        if user_input.lower() == 'quit':
            break
        await generate_and_play_response(user_input)    

if __name__ == "__main__":
    asyncio.run(main_game_loop())
