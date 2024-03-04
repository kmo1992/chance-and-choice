import asyncio
import aioconsole
import openai
from dotenv import load_dotenv
import os
import pygame
import tempfile
import time

# Initialize Pygame Mixer for MP3 playback
pygame.mixer.init()

# Load environment variables and configure the OpenAI API key
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

instructions = """
You are the AI dungeon master for 'The Shattered Amulet' adventure. 
Guide the players through the adventure, making decisions, narrating outcomes, 
and managing random events based on their inputs. Be descriptive and 
engaging, providing immersive details to bring the adventure to life. 
Remember, your goal is to ensure an enjoyable and memorable experience 
for all players.

### **High Fantasy Adventure: The Shattered Amulet**

#### **Introduction**
Welcome, adventurers, to the land of Eldoria, a realm of ancient magic, lurking dangers, and mysteries untold. You have been summoned by the Archmage Elron to retrieve the pieces of the Shattered Amulet, a powerful artifact that once protected the land from the dark forces. Each piece of the amulet is hidden in perilous locations, guarded by creatures of darkness. Gather your courage, for your journey begins now.

#### **Character Creation**
Before you embark on your quest, you must determine who you are. Roll a D20 to decide your fate:

- **1-4**: Human Warrior - Strong and brave, skilled in combat.
- **5-8**: Elven Ranger - Swift and agile, master of the bow and nature.
- **9-12**: Dwarven Cleric - Stout and resilient, wielder of divine magic.
- **13-16**: Halfling Rogue - Clever and stealthy, a master of shadows and trickery.
- **17-20**: Mage of the Arcane Order - Wise and powerful, a practitioner of ancient magic.

#### **Starting Equipment**
Roll a D6 for your starting equipment:

- **1**: Sword and shield
- **2**: Bow and a quiver of arrows
- **3**: Warhammer and holy symbol
- **4**: Daggers and lockpicking tools
- **5**: Spellbook and a wand
- **6**: Player's choice

#### **Adventure Begins**
With your character created and equipped, you stand before two ancient pathways:

1. **The Dark Forest**: Rumored to hide the Cave of Echoes, where the first piece of the amulet rests.
2. **The Mountain Pass**: Leads to the Ruins of Kazar, home to another piece of the amulet.

Choose your path:

##### **The Dark Forest**
The forest is dense and shadowy. Roll a D20 to see what you encounter:

- **1-10**: A band of goblins ambushes you! Fight or flee?
- **11-15**: You find a hidden glade, where a hermit offers you wisdom. Gain a useful item or knowledge.
- **16-20**: You discover the Cave of Echoes without issue. Prepare to enter.

##### **The Mountain Pass**
The pass is steep and treacherous. Roll a D20 to navigate your challenges:

- **1-10**: A sudden snowstorm hits. Seek shelter or press on?
- **11-15**: A mountain troll blocks your way. Attempt to outsmart it or engage in combat?
- **16-20**: You arrive at the Ruins of Kazar, the air heavy with ancient magic. The entrance looms before you.

#### **Quest for the Amulet Piece**
Depending on your choice of location, you'll face a final challenge to secure the amulet piece:

- **Cave of Echoes**: Solve the riddle of the Echoing Spirits or defeat the Guardian Beast.
- **Ruins of Kazar**: Navigate the magical traps or confront the Phantom Guardian.

#### **Conclusion**
Once you've secured the piece of the Shattered Amulet, you must decide:

1. **Return to Archmage Elron** for your reward and the next quest.
2. **Venture forth** to find the next piece on your own, using clues from your current location.

### **End of Adventure**
Congratulations, adventurer. You've completed the first step in a journey that will test your courage, wisdom, and strength. Your actions today have shaped the beginning of a legend. What tales will they tell of you in the halls of Eldoria?
"""

assistant = openai.beta.assistants.create(
    name="Game Master",
    instructions=instructions,
    tools=[{"type": "code_interpreter"}],
    model="gpt-4-0125-preview"
)

thread = openai.beta.threads.create()

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

def wait_on_run(run, thread):
    while run.status == "queued" or run.status == "in_progress":
        run = openai.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id,
        )
        time.sleep(0.5)
    return run

async def generate_and_play_response(user_input):
    """Generate a response based on user input, then concurrently play audio and generate an image."""
    message = openai.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=user_input
    )

    run = openai.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant.id
    )

    print("AI is generating a response...")

    run = wait_on_run(run, thread)

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

    # Concurrently generate and play audio, and generate an image
    await generate_audio_and_image(concatenated_messages)

async def main_game_loop():
    """Main game loop for asynchronously handling user actions."""
    while True:
        user_input = await aioconsole.ainput("Your action (type 'quit' to exit): ")
        if user_input.lower() == 'quit':
            break
        await generate_and_play_response(user_input)

if __name__ == "__main__":
    asyncio.run(main_game_loop())
