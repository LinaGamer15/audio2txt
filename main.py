from flask import Flask, render_template, url_for, send_file
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_wtf import FlaskForm
from wtforms import SelectField, SubmitField
from werkzeug.utils import secure_filename
from pydub import AudioSegment
# create file ignored_file.py with SECRET_KEY
from ignored_file import SECRET_KEY
import speech_recognition as sr
import os
import glob
import shutil

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY

r = sr.Recognizer()


class UploadForm(FlaskForm):
    language = SelectField('Language', choices=['Russian: ru', 'English: en-US'])
    file = FileField(validators=[FileAllowed(['mp3', 'wav'], 'MP3s and WAVs only!'), FileRequired('File is empty!')])
    submit = SubmitField('Upload')


def get_large_audio(path, language, chunksize=60000):
    sound = AudioSegment.from_mp3(path)

    def divide_chunks(sound, chunksize):
        for i in range(0, len(sound), chunksize):
            yield sound[i:i + chunksize]

    chunks = list(divide_chunks(sound, chunksize))
    whole_text = ''
    folder_name = 'audio-chunks'
    if not os.path.isdir(folder_name):
        os.mkdir(folder_name)
    for index, chunk in enumerate(chunks):
        chunk.export(os.path.join(folder_name, f'chunk{index}.wav'), format='wav')
        with sr.AudioFile(os.path.join(folder_name, f'chunk{index}.wav')) as source:
            audio = r.record(source)
        try:
            text = r.recognize_google(audio, language=language)
            whole_text += f'{text} '
        except sr.UnknownValueError:
            print('The text could not be recognized')
    shutil.rmtree(os.path.abspath(folder_name))
    return whole_text


@app.route('/', methods=['GET', 'POST'])
def home():
    files_txt = glob.glob('txt/*.txt')
    for file in files_txt:
        os.remove(file)
    files_wav = glob.glob('*.wav')
    for file in files_wav:
        os.remove(file)
    files_mp3 = glob.glob('*.mp3')
    for file in files_mp3:
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
        if extension == 'wav':
            AudioSegment.from_wav(filename).export(f'{name_file}.mp3', format="mp3")
        text_to_file = get_large_audio(f'{name_file}.mp3', language=form.language.data.split(': ')[1])
        text = open(f'txt/{name_file}.txt', 'w+', encoding='utf-8')
        text.write(text_to_file)
        text.close()
        return send_file(f'txt/{name_file}.txt', mimetype='txt', attachment_filename=f'{name_file}.txt',
                         as_attachment=True)
    return render_template('index.html', form=form)


if __name__ == '__main__':
    app.run(debug=True)
