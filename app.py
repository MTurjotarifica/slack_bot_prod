import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, make_response
from dotenv import load_dotenv
from slack_sdk import WebClient

load_dotenv()

# Initialize the Flask app and the Slack app
app = Flask(__name__)
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

client = WebClient(token=os.environ["SLACK_BOT_TOKEN"])
# Handle incoming slash command requests
@app.route("/slack/command", methods=["POST"])
def handle_slash_command():
    # Parse the command and its parameters from the request
    command = request.form.get("command")
    text = request.form.get("text")
    channel_id = request.form.get("channel_id")

    # Execute the appropriate function based on the command
    if command == "/example":
        slack_app.client.chat_postMessage(channel=response_url, text="it worksssss!")
        response_text = handle_example_command(text)
    else:
        response_text = "Unknown command: {}".format(command)

    # Send the response to the channel
#     slack_app.client.chat_postMessage(channel=response_url, text=response_text)


    # Return an empty response to Slack
    return make_response("", 200)

# Define the function that handles the /example command
def handle_example_command(text):
    return "You entered: {}".format(text)


# Define the function that handles the /hello command

# Add a route for the /hello command
@app.route("/hello", methods=["POST"])
def handle_hello_request():
    # Execute the /hello command function
    slack_app.client.chat_postMessage(response_type= "in_channel", channel='#slack_bot_prod', text="it works!", )
    return "Hello world1" , 200

# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
