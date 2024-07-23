from flask import Flask, request, render_template, Response
import requests
import moviepy.editor as mp
import io
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import translate_v2 as translate
import os

# 환경 변수로 Google Cloud API 키 설정
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "path_to_your_google_cloud_credentials.json"

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/stream')
def stream():
    video_url = request.args.get('url')

    # 비디오 다운로드 및 오디오 추출
    video_response = requests.get(video_url, stream=True)
    video_data = io.BytesIO(video_response.content)
    video = mp.VideoFileClip(video_data)
    audio_path = "audio.wav"
    video.audio.write_audiofile(audio_path)

    # 음성 인식
    client = speech.SpeechClient()
    with io.open(audio_path, "rb") as audio_file:
        content = audio_file.read()
    audio = speech.RecognitionAudio(content=content)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="ja-JP",
    )
    response = client.recognize(config=config, audio=audio)
    transcript = " ".join(result.alternatives[0].transcript for result in response.results)

    # 번역
    translate_client = translate.Client()
    result = translate_client.translate(transcript, target_language="ko")
    translated_text = result["translatedText"]

    # 자막 생성
    subtitles = [(0, video.duration, translated_text)]
    subtitle_clips = []
    for subtitle in subtitles:
        start, end, text = subtitle
        txt_clip = mp.TextClip(text, fontsize=24, color='white', stroke_color='black', stroke_width=1)
        txt_clip = txt_clip.set_position(('center', 'bottom')).set_duration(end - start).set_start(start)
        subtitle_clips.append(txt_clip)

    final_video = mp.CompositeVideoClip([video] + subtitle_clips)

    def generate():
        for frame in final_video.iter_frames():
            yield frame.tobytes()

    return Response(generate(), mimetype='video/mp4')

if __name__ == '__main__':
    app.run(debug=True)
