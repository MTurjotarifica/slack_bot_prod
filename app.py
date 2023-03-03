#mp3 command added 
import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, make_response
from dotenv import load_dotenv
from slack_sdk import WebClient
from threading import Thread
import azure.cognitiveservices.speech as speechsdk

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

load_dotenv()

# Initialize the Flask app and the Slack app
app = Flask(__name__)
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)


client = slack_app.client
# Handle incoming slash command requests
@app.route("/slack/command", methods=["POST"])
def handle_slash_command():
    # Parse the command and its parameters from the request
    command = request.form.get("command")
    text = request.form.get("text")
    channel_id = request.form.get("channel_id")

    # Execute the appropriate function based on the command
    if command == "/example":
        client.chat_postMessage(channel='#slack_bot_prod', text="it worksssss!")
        response_text = handle_example_command(text)
    else:
        response_text = "Unknown command: {}".format(command)

    # Send the response to the channel
#     slack_app.client.chat_postMessage(channel=response_url, text=response_text)


    # Return an empty response to Slack
    return make_response("", 200)
#...........

def backgroundworker_mp3(text, response_url):
    
    # your task
    # The environment variables named "SPEECH_KEY" and "SPEECH_REGION"
    
 
    
    # subscription and speech_region values are obtained from azure portal
    speech_config = speechsdk.SpeechConfig(subscription=os.environ.get('SPEECH_KEY'),
                                           region=os.environ.get('SPEECH_REGION'))
    
    #to output audio to a file called file.wav
    audio_config = speechsdk.audio.AudioOutputConfig(filename=f"{(text[:3]+text[-3:])}.mp3")
    
    # The language of the voice that speaks. en-GB is british accent
    speech_config.speech_synthesis_voice_name='en-GB-RyanNeural'
    
    #creating speech_synthesizer object

    speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config, 
                                                     audio_config=audio_config)
    
    speech_synthesis_result = speech_synthesizer.speak_text_async(text).get()

    if speech_synthesis_result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
        print("Speech synthesized for text [{}]".format(text))
    elif speech_synthesis_result.reason == speechsdk.ResultReason.Canceled:
        cancellation_details = speech_synthesis_result.cancellation_details
        print("Speech synthesis canceled: {}".format(cancellation_details.reason))
        if cancellation_details.reason == speechsdk.CancellationReason.Error:
            if cancellation_details.error_details:
                print("Error details: {}".format(cancellation_details.error_details))
                print("Did you set the speech resource key and region values?")
            
    #payload is required to to send second message after task is completed
    payload = {"text":"your task is complete",
                "username": "bot"}
    
    #uploading the file to slack using bolt syntax for py
    
    #uploading the file to azure blob storage
    container_string=os.environ["CONNECTION_STRING"]
    storage_account_name = "storage4slack"
    container_name = "mp3"
    blob_service_client = BlobServiceClient.from_connection_string (container_string) 
    container_client = blob_service_client.get_container_client(container_name)
    filename = f"{(text[:3]+text[-3:])}.mp3"
    blob_client = container_client.get_blob_client(filename)
    with open(filename, "rb") as data:
        blob_client.upload_blob(data)
        
    try:
        filename=f"{(text[:3]+text[-3:])}.mp3"
        response = client.files_upload(channels='#slack_bot_prod',
                                        file=filename,
                                        initial_comment="Audio: ")
        assert response["file"]  # the uploaded file
    except SlackApiError as e:
        # You will get a SlackApiError if "ok" is False
        assert e.response["ok"] is False
        assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
        print(f"Got an error: {e.response['error']}")

    requests.post(response_url,data=json.dumps(payload))


#mp3 trigger slash command which creates mp3 and posts to slack
@app.route('/mp3_trigger', methods=['POST'])
def mp3_trigger():
    data = request.form
    #we are usging data2 to parse the information
    data2 = request.form.to_dict()
    #print(data)
    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    text = data.get('text')
    response_url = data.get("response_url")
    #event = payload.get('event', {})
    #text = event.get('text')
    greeting_message = "Processing your request. Please wait."
    ending_message = "Process executed successfully"


    client.chat_postMessage(channel='#slack_bot_prod',
                            text="MP3 loading. Please wait."
                            )


    #triggering backgroundworker1 
    thr = Thread(target=backgroundworker_mp3, args=[text, response_url])
    thr.start()


    #returning empty string with 200 response
    return f'{greeting_message}', 200


# Define the function that handles the /example command
def handle_example_command(text):
    return "You entered: {}".format(text)


# Define the function that handles the /hello command

# Add a route for the /hello command
@app.route("/hello", methods=["POST"])
def handle_hello_request():
    data = request.form
    channel_id = data.get('channel_id')
    # Execute the /hello command function
    slack_app.client.chat_postMessage(response_type= "in_channel", channel=channel_id, text="it works!", )
    client.chat_postMessage(response_type= "in_channel", channel='#slack_bot_prod', text="2nd it works!", )
    return "Hello world1" , 200



# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
