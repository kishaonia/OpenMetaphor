
from flask import Flask, render_template, request, jsonify
from pydub.utils import mediainfo
from pydub import AudioSegment
import openai
import os
import subprocess
from config import API_KEY
from datetime import datetime, timedelta
from flask import send_from_directory
from translate import Translator

app = Flask(__name__)
MIME_TYPES = {
    '.mp3': 'audio/mpeg',
    '.wav': 'audio/wav',
    '.flac': 'audio/flac',
    '.m4a': 'audio/mp4',
    '.ogg': 'audio/ogg',
    '.oga': 'audio/ogg',
    '.opus': 'audio/opus',
    '.weba': 'audio/webm',
    '.mp4': 'video/mp4',
    '.mpeg': 'video/mpeg',
    '.ogv': 'video/ogg',
    '.webm': 'video/webm',
    '.3gp': 'video/3gpp',
    '.3g2': 'video/3gpp2',
    '.avi': 'video/x-msvideo',
    '.mov': 'video/quicktime',
    '.wmv': 'video/x-ms-wmv',
    '.mkv': 'video/x-matroska'
}
LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German"
}

# def _translate_helper(data):
#     text_to_translate = data.get('text_to_translate')
#     target_language = data.get('target_language', 'en')
    
#     # Check if the provided target_language is supported
#     if target_language not in LANGUAGES:
#         print(f"Unsupported target language: {target_language}")
#         return text_to_translate  # Just return the original text without translation
    
#     translator = Translator(to_lang=target_language)
#     translated_text = translator.translate(text_to_translate)
#     print("Translated text:", translated_text)
#     return translated_text

MAX_TRANSLATION_CHARS = 5000  # This number is arbitrary, adjust according to your translator's limit

def _translate_helper(data):
    text_to_translate = data.get('text_to_translate')
    target_language = data.get('target_language', 'en')
    
    # Check if the provided target_language is supported
    if target_language not in LANGUAGES:
        print(f"Unsupported target language: {target_language}")
        return text_to_translate  # Just return the original text without translation

    translator = Translator(to_lang=target_language)

    # Split the text to translate into smaller chunks that are under the limit
    text_chunks = [text_to_translate[i:i+MAX_TRANSLATION_CHARS] for i in range(0, len(text_to_translate), MAX_TRANSLATION_CHARS)]
    
    # Translate each chunk
    translated_chunks = [translator.translate(chunk) for chunk in text_chunks]

    # Concatenate translated chunks to get the full translation
    translated_text = "".join(translated_chunks)
    print("Translated text:", translated_text)
    
    return translated_text



def compress_file(input_path, output_path, file_extension):
    if file_extension in ['.mp3', '.wav', '.flac', '.m4a', '.ogg', '.oga', '.opus', '.weba']:
        cmd = ['ffmpeg', '-i', input_path, '-b:a', '64k', output_path]
    else:
        cmd = ['ffmpeg', '-i', input_path, '-b:v', '500k', '-b:a', '64k', output_path]
    subprocess.run(cmd, check=True)
    return output_path

def get_audio_duration(filename):
    """Return the duration of an audio or video file."""
    return float(mediainfo(filename)['duration'])

def split_audio_into_chunks(filename, chunk_duration=7):
    audio = AudioSegment.from_file(filename)
    length_audio = len(audio)
    chunks = []

    for i in range(0, length_audio, chunk_duration * 1000):
        chunks.append(audio[i:i+chunk_duration*1000])
    
    return chunks

def extract_frame_from_video(image_path, timestamp, output_path):
    """Extract a frame from a video at a specific timestamp."""
    cmd = ['ffmpeg', '-ss', str(timestamp), '-i', image_path, '-vframes', '1', '-update', '1', '-pix_fmt', 'yuvj420p', output_path]
    subprocess.run(cmd, check=True)


@app.route('/<filename>')
def serve_image(filename):
    response = send_from_directory('.', filename)
    try:
        os.remove(os.path.join('.', filename))
    except:
        pass  
    return response



@app.route('/', methods=['GET', 'POST'])
def index():
    
    if request.method == 'POST':
        audio_file = request.files.get('audio')
        target_language = 'en'  # Default to English

        if audio_file:
            file_extension = audio_file.filename.rsplit('.', 1)[1].lower()
            content_type = MIME_TYPES.get('.' + file_extension)
            target_language = request.form.get('language', 'en')  # Get language from form, default to 'en' if not found

            if not content_type:
                return jsonify({"error": "Unsupported file format."})

            temp_input_path = f"temp_input.{file_extension}"
            audio_file.save(temp_input_path)

            chunks = split_audio_into_chunks(temp_input_path)
            timestamps = []
            current_time = 0

            extracted_images = []
            transcription_with_timestamp = ""  # Initialize here
            for chunk in chunks:
                temp_chunk_path = f"temp_chunk.{file_extension}"
                chunk.export(temp_chunk_path, format=file_extension.replace('.', ''))
                
                temp_output_path = f"temp_output.{file_extension}"
                compress_file(temp_chunk_path, temp_output_path, '.' + file_extension)

                with open(temp_output_path, 'rb') as compressed_file:
                    openai.api_key = API_KEY
                    response = openai.Audio.transcribe("whisper-1", compressed_file)
                    raw_transcription = response['text']
                    
                    formatted_time = str(timedelta(seconds=int(current_time))).split(":")[-2:]
                    timestamps.append(f"{':'.join(formatted_time)} - {raw_transcription}")

                    if content_type.startswith('video/'):
                        image_path = f"image_paths{current_time}.jpg"
                        extract_frame_from_video(temp_input_path, current_time, image_path)
                        extracted_images.append(image_path)

                    current_time += 7  
                    os.remove(temp_chunk_path)
                    os.remove(temp_output_path)
                    
            transcription_with_timestamp = "\n".join(timestamps)
            os.remove(temp_input_path)

        image_urls = [f"/{os.path.basename(img)}" for img in extracted_images]
        data_to_translate = {
            'text_to_translate': transcription_with_timestamp,
            'target_language': target_language
        }
        translation = _translate_helper(data_to_translate)




    
        return jsonify({
                "transcription": transcription_with_timestamp, 
                "translation": translation,
                "image_paths": image_urls
            })
    return render_template('index.html', transcription="", languages=LANGUAGES)

if __name__ == "__main__":
    app.run(debug=True)