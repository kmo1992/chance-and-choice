import asyncio
import os
import tempfile
from dotenv import load_dotenv
from openai import OpenAI
import pygame
from config import (
    ASSISTANT_MODEL, AUDIO_MODEL, AUDIO_VOICE, CHARACTER_DELAY, INSTRUCTIONS_FILE_PATH
)

# Load environment variables and set the OpenAI API key
load_dotenv()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Initialize Pygame Mixer for audio playback
pygame.mixer.init()

def load_instructions(file_path):
    """Load instructions from a specified file path."""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

instructions = load_instructions(INSTRUCTIONS_FILE_PATH)

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
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmpfile:
            response = client.audio.speech.create(
                model=AUDIO_MODEL,
                voice=AUDIO_VOICE,
                input=response_text
            )
            
            response.stream_to_file(tmpfile.name)

            typing_task = asyncio.create_task(type_text(response_text))
            play_audio_task = asyncio.create_task(play_mp3(tmpfile.name))

            await typing_task
            await play_audio_task

            # Clean up the temporary file
            os.unlink(tmpfile.name)
    except Exception as e:
        print(f"Error generating or playing audio: {e}")

async def main_game_loop():
    """Main game loop to handle user input and generate responses."""
    messages = [{"role": "system", "content": instructions}]
    
    while True:
        user_input = await asyncio.get_event_loop().run_in_executor(None, input, "\n\nuser (type 'quit' to exit) > ")
        if user_input.lower() == 'quit':
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=ASSISTANT_MODEL,
                messages=messages
            )

            assistant_response = response.choices[0].message.content
            messages.append({"role": "assistant", "content": assistant_response})

            print("\nassistant > ", end="", flush=True)
            await generate_and_play_audio(assistant_response)

        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main_game_loop())