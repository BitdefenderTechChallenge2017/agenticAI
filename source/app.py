import uuid, base64, os
from flask import Flask, render_template, request, stream_with_context, make_response, Response
from agno.memory.v2 import Memory
from helpers import *

app = Flask(__name__)
_memory = Memory() # Shared memory for agents

# Home page
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# REST method for invoking a team of AI team agents
@app.route('/team', methods=['get'])
def ask_team():
    try:
        # Get the session ID, if any
        session_id = request.headers.get('X-Session-ID')

        # Create a session ID if none was provided
        if not session_id:
            session_id = str(uuid.uuid4())

        # Create a team
        team = create_team(_memory)
        team.session_id = session_id

        # Get the user input and generate a response
        user_input = request.args.get('input')
        output = team.run(user_input, stream=True)
        response = make_response(stream_with_context(generate(output)))
        response.headers['X-Session-ID'] = session_id
        return response

    except Exception as e:
        output = f"I'm sorry, but something went wrong. ({str(e)})"
        response = make_response(stream_with_context(generate(output)))
        response.headers['X-Session-ID'] = session_id
        return response
    
# Generator for streaming output
def generate(chunks):
    for chunk in chunks:
        yield chunk.content

# REST method for downloading generated images
@app.route('/image', methods=['get'])
def get_image():
    src = ''

    if os.path.exists(IMAGE_PATH):
        with open(IMAGE_PATH, 'rb') as image_file:
            image_bytes = image_file.read()

        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        src = f'data:image/png;base64,{base64_image}'
        os.remove(IMAGE_PATH) # Clean up

    return Response(src)
