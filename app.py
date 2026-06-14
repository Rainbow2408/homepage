import os
from flask import Flask, render_template, request, jsonify
from werkzeug.exceptions import HTTPException
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import official OpenAI client
from openai import OpenAI

app = Flask(__name__)
# Ensure unhandled exceptions are caught by our errorhandlers, not propagated to WSGI server
app.config["PROPAGATE_EXCEPTIONS"] = False

# Global error handlers — ensure API routes always return JSON, never HTML
@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Handle werkzeug HTTP errors (4xx/5xx) and return JSON."""
    return jsonify(success=False, error=f"HTTP {e.code}: {e.description}"), e.code

@app.errorhandler(Exception)
def handle_exception(e):
    """Return JSON for any unhandled non-HTTP exception."""
    # Re-raise HTTPExceptions so handle_http_exception takes over
    if isinstance(e, HTTPException):
        return handle_http_exception(e)
    return jsonify(success=False, error=f"伺服器內部錯誤：{str(e)}"), 500

# Initialize OpenAI client safely (lazy loaded)
client = None
def get_openai_client():
    global client
    if client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise Exception("未設定 OPENAI_API_KEY。請確認已在 Render 後台的 Environment Variables 中設定您的 OpenAI API 金鑰。")
        client = OpenAI(api_key=api_key)
    return client

# User-requested text generation function, updated to use official OpenAI SDK
def ask_ai(prompt):
    openai_client = get_openai_client()
    response = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

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
def generate_image_with_fallback(prompt, size):
    openai_client = get_openai_client()
    is_low_res = size in ["256x256", "512x512"]
    pref_model = os.getenv("OPENAI_IMAGE_MODEL")
    
    if is_low_res:
        # For low-res, dall-e-2 is the only model that supports 256x256/512x512
        model_sequence = ["dall-e-2"]
        if pref_model and pref_model not in model_sequence:
            model_sequence.insert(0, pref_model)
    else:
        # For standard/high-res, try gpt-image-1 first (latest), then dall-e-3, then dall-e-2
        model_sequence = ["gpt-image-1", "dall-e-3", "dall-e-2"]
        if pref_model:
            if pref_model in model_sequence:
                model_sequence.remove(pref_model)
            model_sequence.insert(0, pref_model)

    errors = []
    for model in model_sequence:
        active_size = size
        # dall-e-2 only supports square dimensions
        if model == "dall-e-2":
            if active_size not in ["1024x1024", "512x512", "256x256"]:
                active_size = "1024x1024"
                
        try:
            response = openai_client.images.generate(
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
            image_url, active_model, size_changed = generate_image_with_fallback(prompt, size)
            
            # Formulate user warning if fallback occurred (primary model is gpt-image-1)
            warning_msg = None
            primary_model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
            if active_model != primary_model:
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
