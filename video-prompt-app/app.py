from flask import Flask, render_template, request
from openai import OpenAI
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import os
import base64
import mimetypes
from datetime import datetime

usage = {}

def can_use(ip):
    today = datetime.now().date()

    if ip not in usage:
        usage[ip] = {"count": 0, "date": today}

    if usage[ip]["date"] != today:
        usage[ip] = {"count": 0, "date": today}

    if usage[ip]["count"] >= 3:
        return False

    usage[ip]["count"] += 1
    return True

load_dotenv()
VIP_PASSWORD = os.getenv("VIP_PASSWORD")
client = OpenAI()

app = Flask(__name__)
UPLOAD_FOLDER = "static"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def image_to_base64(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def make_video_prompt(user_text, image_path):
    image_base64 = image_to_base64(image_path)

    mime_type, _ = mimetypes.guess_type(image_path)
    if mime_type not in ["image/jpeg", "image/png", "image/webp", "image/gif"]:
        raise ValueError("対応していない画像形式です。jpg / png / webp / gif を使ってください。")

    response = client.responses.create(
        model="gpt-4o-mini",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"""
You are an expert prompt writer for video generation AI such as Kling or Pika.

Look at the uploaded image and create a high-quality English prompt for image-to-video generation.

User request:
{user_text}

Requirements:
- 5-second video
- natural next motion from the image
- cinematic and realistic
- simple human movement
- avoid distorted faces, bad hands, extra fingers
- output ONLY the English prompt
"""
                    },
                    {
                        "type": "input_image",
                        "image_url": f"data:{mime_type};base64,{image_base64}"
                    }
                ]
            }
        ]
    )

    return response.output_text

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    image_filename = None
    error = None

    if request.method == "POST":
        
        vip_code = request.form.get("vip_code", "")

        if vip_code != VIP_PASSWORD:
            ip = request.remote_addr

        if not can_use(ip):
            error = "今日は無料回数を使い切りました。合言葉がある人は入力してね♡"
            return render_template("index.html", result=None, image=None, error=error)
        user_text = request.form["text"]

        if user_text == "エラーテスト":
            error = "ごめんね♡ 今、全世界のみんながAIを使いすぎて混み合っています。少し時間をおいて、もう一度試してみてください。"
            return render_template("index.html", result=None, image=None, error=error)
        user_text = request.form["text"]
        file = request.files["image"]

        if not file or file.filename == "":
            error = "画像を選択してください。"
        elif not allowed_file(file.filename):
            error = "画像は jpg / jpeg / png / webp / gif のどれかにしてください。"
        else:
            filename = secure_filename(file.filename)
            image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(image_path)
            image_filename = filename

            try:
              

                result = make_video_prompt(user_text, image_path)

            except Exception as e:
                error_message = str(e)

                if "rate_limit" in error_message.lower() or "429" in error_message or "quota" in error_message.lower():
                    error = "ごめんね♡ 今、全世界のみんながAIを使いすぎて混み合っています。少し時間をおいて、もう一度試してみてください。"
                elif "invalid image" in error_message.lower() or "valid image" in error_message.lower():
                    error = "画像がうまく読み込めませんでした。JPG・PNG・WEBPの画像でもう一度試してみてください。"
                else:
                    error = "ごめんね♡ うまく生成できませんでした。少し時間をおいてもう一度試してみてください。"
            finally:
                if os.path.exists(image_path):
                   os.remove(image_path)

    return render_template("index.html", result=result, image=None, error=error)

if __name__ == "__main__":
    app.run(debug=True)