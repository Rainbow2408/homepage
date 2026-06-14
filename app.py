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

# Helper function to generate images with fallback models (handles deprecation of dall-e series)
def generate_image_with_fallback(client, prompt, size):
    is_low_res = size in ["256x256", "512x512"]
    pref_model = os.getenv("OPENAI_IMAGE_MODEL")
    
    if is_low_res:
        # Prioritize 1.5, then 2, then legacy dall-e-2
        model_sequence = ["gpt-image-1.5", "gpt-image-2", "dall-e-2"]
        if pref_model:
            if pref_model in model_sequence:
                model_sequence.remove(pref_model)
            model_sequence.insert(0, pref_model)
    else:
        # Prioritize 2, then 1.5, then legacy dall-e-3 and dall-e-2
        model_sequence = ["gpt-image-2", "gpt-image-1.5", "dall-e-3", "dall-e-2"]
        if pref_model:
            if pref_model in model_sequence:
                model_sequence.remove(pref_model)
            model_sequence.insert(0, pref_model)

    errors = []
    for model in model_sequence:
        active_size = size
        # gpt-image-1.5 and dall-e-2 only support square dimensions
        if model in ["gpt-image-1.5", "dall-e-2"]:
            if active_size not in ["1024x1024", "512x512", "256x256"]:
                active_size = "1024x1024"
                
        try:
            response = client.images.generate(
                model=model,
                prompt=prompt,
                size=active_size,
                n=1
            )
            return response.data[0].url, model, (active_size != size)
        except Exception as e:
            errors.append(f"{model}: {str(e)}")
            
    raise Exception(" | ".join(errors))

@app.route('/ai-image', methods=['GET', 'POST'])
def ai_image():
    if request.method == 'POST':
        data = request.get_json() or {}
        prompt = data.get('prompt', '').strip()
        size = data.get('size', '1024x1024')
        
        if not prompt:
            return jsonify(success=False, error="圖片文字描述不能為空"), 400
            
        try:
            image_url, active_model, size_changed = generate_image_with_fallback(client, prompt, size)
            
            # Formulate user warning if fallback occurred
            warning_msg = None
            if active_model != os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2") and active_model != "gpt-image-2":
                warning_msg = f"系統偵測到您的 API 金鑰不支援預設模型，已自動為您降級至 {active_model} 生成圖片！"
                if size_changed:
                    warning_msg += " (因模型限制，已將尺寸調整為 1024x1024 正方形)"
            
            return jsonify(success=True, url=image_url, warning=warning_msg)
        except Exception as e:
            return jsonify(success=False, error=str(e)), 500
            
    return render_template('ai_image.html')

if __name__ == '__main__':
    host = os.getenv('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_RUN_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() in ['true', '1', 'yes']
    
    app.run(host=host, port=port, debug=debug)
