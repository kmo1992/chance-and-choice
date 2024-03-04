# chance-and-choice

Your AI dungeon master awaits!

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

- Python 3.6 or higher
- pip (or pip3 for some macOS and Linux setups)

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/kmo1992/chance-and-choice.git
   cd chance-and-choice
   ```

2. **Set Up a Virtual Environment**

   - macOS/Linux:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```
   - Windows:
     ```bash
     py -m venv venv
     .\venv\Scripts\activate
     ```

3. **Install Dependencies**

   With the virtual environment activated, install the necessary packages:

   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**

   Create a `.env` file in the root of your project and add your OpenAI API key:

   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

   This file should not be committed to your version control system. Add `.env` to your `.gitignore` file.

### Running the Application

To start the game, run:

```bash
python start_game.py
```

Follow the on-screen prompts to interact with the game.

## Contributing

Interested in contributing? We love pull requests! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and submission process.

## Authors

- **Kevin Oliver**

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details.
