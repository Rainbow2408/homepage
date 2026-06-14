import os
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import official OpenAI client
from openai import OpenAI

app = Flask(__name__)

# Initialize OpenAI client with API Key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# User-requested custom text generation function
def ask_ai(prompt):
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt
    )
    return response.output_text

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/ai-chat', methods=['GET', 'POST'])
def ai_chat():
    if request.method == 'POST':
        data = request.get_json() or {}
        prompt = data.get('prompt', '').strip()
        
        if not prompt:
            return jsonify(success=False, error="問題內容不能為空"), 400
        
        try:
            reply = ask_ai(prompt)
            return jsonify(success=True, reply=reply)
        except Exception as e:
            return jsonify(success=False, error=str(e)), 500
            
    return render_template('ai_chat.html')

@app.route('/ai-image', methods=['GET', 'POST'])
def ai_image():
    if request.method == 'POST':
        data = request.get_json() or {}
        prompt = data.get('prompt', '').strip()
        size = data.get('size', '1024x1024')
        
        if not prompt:
            return jsonify(success=False, error="圖片文字描述不能為空"), 400
            
        # Standard sizes supported by DALL-E models
        # DALL-E 3 supports 1024x1024, 1024x1792, 1792x1024
        # DALL-E 2 supports 512x512, 256x256, 1024x1024
        model = "dall-e-3"
        if size in ["256x256", "512x512"]:
            model = "dall-e-2"
            
        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                n=1
            )
            image_url = response.data[0].url
            return jsonify(success=True, url=image_url)
        except Exception as e:
            return jsonify(success=False, error=str(e)), 500
            
    return render_template('ai_image.html')

if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']
    
    app.run(host=host, port=port, debug=debug)
