from dotenv import load_dotenv
import os
import openai
import pygame
from pathlib import Path
import tempfile

# Initialize Pygame Mixer
pygame.mixer.init()

# Load environment variables
load_dotenv()

# Configure your OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

def play_audio_from_file(audio_file_path):
    wave_obj = sa.WaveObject.from_wave_file(audio_file_path)
    play_obj = wave_obj.play()
    play_obj.wait_done()  # Wait until audio file finishes playing

def play_mp3(audio_file_path):
    # Load and play an MP3 audio file
    pygame.mixer.music.load(audio_file_path)
    pygame.mixer.music.play()
    # Wait for the music to play before proceeding
    while pygame.mixer.music.get_busy():
        pygame.time.Clock().tick(10)

def generate_and_play_response(user_input):
    # Assuming 'openai.audio.speech.create' and 'openai.ChatCompletion.create' are hypothetical functions
    # based on OpenAI's capabilities. Adjust according to the actual API functions and parameters.
    prompt_response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": "You are the dungeon master. The adventure begins!"},
                  {"role": "user", "content": user_input}]
    )

    response_text = prompt_response.choices[0].message.content
    print("AI is generating a response...")

    # Generate speech from response text
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmpfile:
        prompt_speech_response = openai.audio.speech.create(
            model="tts-1",
            voice="fable",
            input=response_text
        )
        prompt_speech_response.write_to_file(tmpfile.name)
        # Play the audio file
        play_mp3(tmpfile.name)

# Main game loop
while True:
    user_input = input("Your action (type 'quit' to exit): ")
    if user_input.lower() == 'quit':
        break
    generate_and_play_response(user_input)
