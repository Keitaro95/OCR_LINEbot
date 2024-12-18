import os
import base64
import json
from PIL import Image
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def process_image(image_content):
    client = OpenAI(api_key=os.getenv("GPT_API_KEY"))
    json_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "company_name": {"type": "string"},
            "address": {"type": "string"},
            "post_code": {"type": "string"},
            "phone_number": {"type": "string"},
            "mail_address": {"type": "string"},
        },
        "required": ["name", "company_name", "address", "post_code", "phone_number", "mail_address"]
    }

    base64_image = base64.b64encode(image_content).decode('utf-8')

    completion = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "あなたは日本語で応答する優秀な秘書です。"},
            {"role": "user",
             "content": [
                 {"type": "text",
                  "text": """\
    ## 命令
    この画像に表示されている内容について回答してください。
    氏名(name), 会社名(company_name), 住所(address), 郵便番号(post_code)、電話番号(phone_number)、メールアドレス(mail_address)を教えて下さい。
    ## Output
    """},
                 {
                     "type": "image_url",
                     "image_url": {
                         "url":  f"data:image/png;base64,{base64_image}"
                     },
                 },
             ],
             }
        ],
        functions=[
            {"name": "extract_text", "parameters": json_schema}
        ],
        function_call={"name": "extract_text"},
    )
    return json.loads(completion.choices[0].message.function_call.arguments)

