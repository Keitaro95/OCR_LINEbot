import os
import sys
from fastapi import Request, FastAPI, HTTPException
from linebot.v3.webhook import WebhookParser
from linebot.v3.messaging import (
    AsyncApiClient,
    AsyncMessagingApi,
    Configuration,
    TextSendMessage,
)
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import gspread

from ocr_handler import process_image


channel_secret = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
channel_access_token = os.getenv('LINE_CHANNEL_SECRET')

configuration = Configuration(access_token=channel_access_token)

app = FastAPI()

async_api_client = AsyncApiClient(configuration)
line_bot_api = AsyncMessagingApi(async_api_client)
parser = WebhookParser(channel_secret)



def auth():
    # Google Sheets APIの設定
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    credentials = ServiceAccountCredentials.from_json_keyfile_name('json/gcp-credentials.json', scope)
    gc = gspread.authorize(credentials)
    # 書き込むworksheetはここに登録する
    worksheet = gc.open_by_key(os.getenv('SP_SHEET_KEY')).worksheet(os.getenv('SP_SHEET'))  # 修正: open() から open_by_key() へ変更
    return worksheet

# スプレッドシートへのアップロード関数
def upload_to_sheet(json_data):
    worksheet = auth()
    df = pd.DataFrame(worksheet.get_all_records()) 
    new_row = pd.DataFrame([[json_data['name'], json_data['company_name'], json_data['address'], json_data['post_code'], json_data['phone_number'], json_data['mail_address']]], columns=['name', 'company_name', 'address', 'post_code', 'phone_number', 'mail_address'])
    df = pd.concat([df, new_row], ignore_index=True)
    worksheet.append_row(new_row.values.flatten().tolist())
    return worksheet


@app.get('/')
def root():
    return {"title": "Echo Bot"}


@app.post("/callback")
async def handle_callback(request: Request):
    signature = request.headers['x_line_signature']
    # get request body as text
    body = await request.body()
    body = body.decode()
    try:
        background_tasks.add_task(
            handler.handle,
            body.decode("utf-8"),
            x_line_signature
        )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return 'OK'


@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    message_content = line_bot_api.get_message_content(event.message.id)
    try:
        # OCR処理
        ocr_json = process_image(message_content.content)
        app.logger.info(f"OCR結果: {ocr_json}")
        line_bot_api.reply_message(
            event.reply_token,
                TextSendMessage(text="名刺情報：\n" + "\n".join([f"{key}: {value}" for key, value in ocr_json.items()]))
            )
        app.logger.info("名刺情報を正常に処理し、スプレッドシートに保存しました。")
        # スプレッドシートに書き込み
        upload_to_sheet(ocr_json)
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="名刺情報を正常に処理し、スプレッドシートに保存しました。")
        )
        app.logger.info("名刺情報を正常に処理し、スプレッドシートに保存しました。")
    except Exception as e:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"エラーが発生しました: {str(e)}")
        )
        app.logger.error(f"エラーが発生しました: {str(e)}")




if __name__ == '__main__':
    basedir = os.path.abspath(os.path.dirname(__name__))
    log = logging.getLogger('werkzeug')
    log.setLevel(logging.ERROR)
    if os.getenv('ENVIRONMENT', 'development') == 'development':
        log_file_path = os.path.join(basedir, 'flaskr', 'config', 'development', 'logger.conf')
        debug_mode = True #開発環境ではtrue
    else:
        log_file_path = os.path.join(basedir, 'flaskr', 'config', 'production', 'logger.conf')
        debug_mode = False #本番環境ではfalse
    logging.config.fileConfig(fname=log_file_path)
    from flask.logging import default_handler
    app.logger.removeHandler(default_handler) #デフォルトのログがなくなる
    app.run(debug=debug_mode)
