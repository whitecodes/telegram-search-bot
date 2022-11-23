from flask import Flask, request, redirect
from database import DBSession, Message, User, Chat
from datetime import datetime
import json
import ijson

ALLOWED_EXTENSIONS = {'json'}

app = Flask(__name__, static_url_path='',
            static_folder='static')


def insert_chat_or_do_nothing(chat_id, title):
    session = DBSession()
    target_chat = session.query(Chat).get(chat_id)
    if not target_chat:
        new_chat =  Chat(id=chat_id, title=title, enable=False)
        session.add(new_chat)
        session.commit()
    session.close()


def insert_user_or_do_nothing(user_id, fullname, username):
    session = DBSession()
    target_user = session.query(User).get(user_id)
    if not target_user:
        new_user = User(id=user_id, fullname=fullname, username=username)
        session.add(new_user)
        session.commit()
    session.close()


def insert_messages(chat_id, messages):
    fail_count = 0
    fail_messages = []
    success_count = 0
    for message in messages:
        if 'from_id' not in message :
            continue
        elif 'user' not in message ['from_id']:
            continue
        insert_user_or_do_nothing(message['from_id'][4:], message['from'], message['from'])
        if isinstance(message['text'], list):
            msg_text = ''
            for obj in message['text']:
                if isinstance(obj, dict):
                    msg_text += obj['text']
                else:
                    msg_text += obj
        else:
            msg_text = message['text']

        if msg_text =='':
            msg_text = '[其他消息]'
        message_date = datetime.strptime(message['date'], '%Y-%m-%dT%H:%M:%S')
        new_msg = Message(id=message['id'], link='https://t.me/c/{}/{}'.format(str(chat_id)[4:],message['id']), text=msg_text, video='', photo='',
                          audio='', voice='', type='text', category='', from_id=message['from_id'][4:], from_chat=chat_id,date=message_date)
        
        session = DBSession()
        try:
            session.add(new_msg)
            session.commit()
            success_count += 1
        except Exception as e:
            print(e)
            fail_count += 1
            fail_messages.append(str(message))
        session.close()

    return success_count, fail_count, fail_messages


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            Flask('No file part')
            return redirect(request.url)
        file = request.files['file']
        if file.filename == '':
            Flask('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            file_content = file.read().decode('utf-8')
            history_json = json.loads(file_content)
            if 'supergroup' not in history_json['type']:
                return '<!doctype html><h2>导入结果</h2><p>导入出错：群组非supergroup</p>'
            else:
                edit_id = history_json['id'] if history_json['id'] < 0 else int('-100' + str(history_json['id']))
                insert_chat_or_do_nothing(edit_id,history_json['name'])
                success_count, fail_count, fail_messages = insert_messages(edit_id,history_json['messages'])
                fail_text = ''
                for fail_message in fail_messages:
                    fail_text += '<p><i>{}</i></p>'.format(fail_message) 
            return '<!doctype html><h2>导入结果</h2><p>导入群组: {} ({})</p><p>导入成功: {}条</p><p>导入失败: {}条</p>{}'.format(history_json['name'],history_json['id'],success_count,fail_count,fail_text)
    return '''
    <!doctype html>
    <title>从历史记录导入</title>
    <h1>上传导出的记录文件(.json)</h1>
    <form method=post enctype=multipart/form-data>
      <input type=file name=file>
      <input type=submit value=Upload>
    </form>
    '''


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5006)
