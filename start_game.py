# start_game.py

import asyncio
import os
import tempfile
from typing import override
import aioconsole
from dotenv import load_dotenv
import openai
import pygame
from config import (
    ASSISTANT_MODEL, AUDIO_MODEL, AUDIO_VOICE, CHARACTER_DELAY, INSTRUCTIONS_FILE_PATH
)

# Load environment variables and set the OpenAI API key
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# Initialize Pygame Mixer for audio playback
pygame.mixer.init()

def load_instructions(file_path):
    """Load instructions from a specified file path."""
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
    """Play an MP3 audio file asynchronously."""
    try:
        pygame.mixer.music.load(audio_file_path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Error playing audio: {e}")

async def type_text(text):
    """Simulate typing out text one character at a time, based on a configured delay."""
    for char in text:
        print(char, end='', flush=True)
        await asyncio.sleep(CHARACTER_DELAY)

async def generate_and_play_audio(response_text):
    """Generate audio from response text, simulate typing, and play the audio."""
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as tmpfile:
            with openai.audio.speech.with_streaming_response.create(
                model=AUDIO_MODEL,
                voice=AUDIO_VOICE,
                input=response_text
            )as response:
                response.stream_to_file(tmpfile.name)

            typing_task = asyncio.create_task(type_text(response_text))
            play_audio_task = asyncio.create_task(play_mp3(tmpfile.name))

            await typing_task
            await play_audio_task
    except Exception as e:
        print(f"Error generating or playing audio: {e}")

class EventHandler(openai.AssistantEventHandler):
    """Custom event handler to process and queue text for audio playback."""
    def __init__(self):
        super().__init__()
        self.text_buffer = ""
        self.audio_queue = asyncio.Queue()

    @override
    def on_text_created(self, text) -> None:
        print(f"\nassistant > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        """Accumulate text deltas and queue complete paragraphs for audio playback."""
        self.text_buffer += delta.value

        while '\n\n' in self.text_buffer:
            break_index = self.text_buffer.index('\n\n') + 2
            paragraph = self.text_buffer[:break_index]
            self.audio_queue.put_nowait(paragraph)
            self.text_buffer = self.text_buffer[break_index:]

    async def audio_playback_worker(self):
        """Process queued text for audio playback in a background task."""
        while True:
            text_to_speak = await self.audio_queue.get()
            await generate_and_play_audio(text_to_speak)
            self.audio_queue.task_done()

    def end_of_stream(self):
        """Queue any remaining text in the buffer for playback at stream end."""
        if self.text_buffer.strip():
            self.audio_queue.put_nowait(self.text_buffer)
            self.text_buffer = ""

    def on_tool_call_created(self, tool_call):
        print(f"\nassistant > {tool_call.type}\n", flush=True)

    def on_tool_call_delta(self, delta, snapshot):
        if delta.type == 'code_interpreter':
            if delta.code_interpreter.input:
                print(delta.code_interpreter.input, end="", flush=True)
            if delta.code_interpreter.outputs:
                print(f"\n\noutput >", flush=True)
            if delta.code_interpreter.outputs is not None:
                for output in delta.code_interpreter.outputs:
                    if output.type == "logs":
                        print(f"\n{output.logs}", flush=True)

async def main_game_loop():
    """Main game loop to handle user input and generate responses."""
    
    while True:
        user_input = await aioconsole.ainput("\n\nuser (type 'quit' to exit) > ")
        if user_input.lower() == 'quit':
            break

        event_handler = EventHandler()
        worker_task = asyncio.create_task(event_handler.audio_playback_worker())

        try:
            message = openai.beta.threads.messages.create(
                thread_id=thread.id,
                role="user",
                content=user_input
            )

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

            await event_handler.audio_queue.join()  # Ensure all audio has been played
        finally:
            worker_task.cancel()
            try:
                await worker_task  # Ensure the task is cancelled properly
            except asyncio.CancelledError:
                pass  # Expected upon cancellation

if __name__ == "__main__":
    asyncio.run(main_game_loop())
