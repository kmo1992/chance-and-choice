import asyncio
import aioconsole
import openai
from dotenv import load_dotenv
import os
import pygame
import tempfile

# Initialize Pygame Mixer for MP3 playback
pygame.mixer.init()

# Load environment variables and configure the OpenAI API key
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

async def play_mp3(audio_file_path):
    """Asynchronously play an MP3 audio file without blocking."""
    pygame.mixer.music.load(audio_file_path)
    pygame.mixer.music.play()
    # No waiting/blocking here, allowing other tasks to run concurrently

async def generate_audio_and_image(response_text):
    """Generate audio from the response text and play it, while also generating an image."""
    # Generate speech from response text and play it immediately
    with tempfile.NamedTemporaryFile(delete=True, suffix='.mp3') as tmpfile:
        prompt_speech_response = openai.audio.speech.create(
            model="tts-1",
            voice="fable",
            input=response_text
        )
        prompt_speech_response.write_to_file(tmpfile.name)
        await play_mp3(tmpfile.name)

    # Generate an image based on the response text
    hook_image_response = openai.images.generate(
        model="dall-e-3",
        prompt=response_text,
        n=1,
        size="1024x1024"
    )
    image_url = hook_image_response.data[0].url
    print('Scene URL:', image_url)

async def generate_and_play_response(user_input):
    """Generate a response based on user input, then concurrently play audio and generate an image."""
    prompt_response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are the dungeon master. The adventure begins!"},
                  {"role": "user", "content": user_input}]
    )
    response_text = prompt_response.choices[0].message.content
    print("AI is generating a response...")

    # Concurrently generate and play audio, and generate an image
    await generate_audio_and_image(response_text)

async def main_game_loop():
    """Main game loop for asynchronously handling user actions."""
    while True:
        user_input = await aioconsole.ainput("Your action (type 'quit' to exit): ")
        if user_input.lower() == 'quit':
            break
        await generate_and_play_response(user_input)

if __name__ == "__main__":
    asyncio.run(main_game_loop())
