from flask import Flask, render_template, url_for, send_file
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from werkzeug.utils import secure_filename
from pydub import AudioSegment
from pydub.silence import split_on_silence
# create file ignored_file.py with SECRET_KEY
from ignored_file import SECRET_KEY
import speech_recognition as sr
import os
import glob


app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

r = sr.Recognizer()


class UploadForm(FlaskForm):
    language = SelectField('Language', choices=['Russian: ru', 'English: en-US'])
    file = FileField(validators=[FileAllowed(['mp3', 'wav'], 'MP3s and WAVs only!'), FileRequired('File is empty!')])
    submit = SubmitField('Upload')


def get_large_audio(path, language):
    sound = AudioSegment.from_wav(path)
    chunks = split_on_silence(sound, min_silence_len=500, silence_thresh=-16)
    folder_name = 'audio-chunks'
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    whole_text = ''
    for i, audio_chunk in enumerate(chunks, start=1):
        chunk_filename = os.path.join(folder_name, f'chunk{i}.wav')
        audio_chunk.export(chunk_filename, format='wav')
        with sr.AudioFile(chunk_filename) as source:
            audio = r.record(source)
            try:
                text = r.recognize_google(audio, language, show_all=True)
            except sr.RequestError:
                try:
                    with sr.AudioFile(path) as source:
                        audio_data = r.record(source)
                        whole_text = r.recognize_google(audio_data, language=language)
                        break
                except sr.UnknownValueError:
                    print('UnknownValueError')
            except sr.UnknownValueError:
                print('UnknownValueError')
            else:
                whole_text += text
    return whole_text


@app.route('/', methods=['GET', 'POST'])
def home():
    files_txt = glob.glob('txt/*.txt')
    for file in files_txt:
        os.remove(file)
    form = UploadForm()
    if form.validate_on_submit():
        folder_txt = 'txt'
        if not os.path.isdir(folder_txt):
            os.mkdir(folder_txt)
        filename = secure_filename(form.file.data.filename)
        form.file.data.save(filename)
        extension = filename.split('.')[1]
        name_file = filename.split('.')[0]
        if extension == 'mp3':
            sound = AudioSegment.from_mp3(filename)
            filename = f'{name_file}.wav'
            sound.export(f'{name_file}.wav', format='wav')
        text_to_file = get_large_audio(filename, language=form.language.data.split(': ')[1])
        text = open(f'txt/{name_file}.txt', 'w+', encoding='utf-8')
        text.write(text_to_file)
        text.close()
        files_wav = glob.glob('*.wav')
        for file in files_wav:
            os.remove(file)
        files_mp3 = glob.glob('*.mp3')
        for file in files_mp3:
            os.remove(file)
        return send_file(f'txt/{name_file}.txt', mimetype='txt', attachment_filename=f'{name_file}.txt',
                         as_attachment=True)

    return render_template('index.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)
