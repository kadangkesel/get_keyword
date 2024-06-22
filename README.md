# GetKey{word}

GetKey{word} is a desktop application that uses Google Generative AI to generate short descriptions and relevant tags for selected images. 
This application also edits the image metadata to include the generated descriptions and tags.

## Features

- **Select Directory**: Choose a directory containing the images to be processed.
- **Enter API Key**: Enter your Google Generative AI API Key.
- **Process Images**: Generates descriptions and tags for each image in the selected directory and saves them as image metadata.

## Prerequisites

Ensure you have the following prerequisites installed before running this application:

- Python 3.6 or higher
- Pip (Python Package Installer)

## Installation

1. Clone this repository to your local machine:

   ```bash
   git clone https://github.com/kadangkesel/get_keyword.git
   ```
   and then
   ```bash
   cd get_keyword
   ```
   
2. Create and activate a virtual environment (optional but recommended):

   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows use `venv\Scripts\activate`
    ```
3.Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4.Run the application:

  ```bash
  python main.py
   ```
