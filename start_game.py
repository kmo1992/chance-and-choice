# main.py

import asyncio
import os
import tempfile

import aioconsole
from dotenv import load_dotenv
import openai
import pygame
from config import (ASSISTANT_MODEL, AUDIO_MODEL, AUDIO_VOICE, IMAGE_MODEL, IMAGE_SIZE, INSTRUCTIONS_FILE_PATH)

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

async def generate_and_play_audio(response_text):
    """Generate audio from the response text and play it."""
    try:
        with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as tmpfile:
            prompt_speech_response = openai.audio.speech.create(
                model=AUDIO_MODEL,
                voice=AUDIO_VOICE,
                input=response_text
            )
            # Assuming 'write_to_file' is a method that writes the audio to a file
            prompt_speech_response.write_to_file(tmpfile.name)
            await play_mp3(tmpfile.name)
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

async def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        await asyncio.sleep(0.25)
    return run

async def generate_and_play_response(user_input):
    """Generate a response based on user input, then concurrently play audio and generate an image."""
    try:
        message = openai.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        run = openai.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=assistant.id
        )

        print("AI is generating a response...\n")

        run = await wait_on_run(run, thread)

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

        # Log the response for the user to see
        print(concatenated_messages + "\n")

        # Create tasks for audio and image generation to run concurrently
        audio_task = asyncio.create_task(generate_and_play_audio(concatenated_messages))
        image_task = asyncio.create_task(generate_and_display_image(concatenated_messages))

        # Wait for the image task to complete first to ensure its output is handled as soon as it's ready
        await image_task
        # Then wait for the audio task, ensuring it also completes
        await audio_task
    except Exception as e:
        print(f"Error in generating and playing response: {e}")

async def main_game_loop():
    """Main game loop for asynchronously handling user actions."""

    while True:
        user_input = await aioconsole.ainput("Your action (type 'quit' to exit): ")
        if user_input.lower() == 'quit':
            break
        await generate_and_play_response(user_input)

if __name__ == "__main__":
    asyncio.run(main_game_loop())
