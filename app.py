import os
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request, make_response
from dotenv import load_dotenv
load_dotenv()

# Initialize the Flask app and the Slack app
app = Flask(__name__)
slack_app = App(
    token=os.environ["SLACK_BOT_TOKEN"],
    signing_secret=os.environ["SLACK_SIGNING_SECRET"]
)

# Handle incoming slash command requests
@app.route("/slack/command", methods=["POST"])
def handle_slash_command():
    # Parse the command and its parameters from the request
    command = request.form.get("command")
    text = request.form.get("text")

    # Execute the appropriate function based on the command
    if command == "/example":
        response_text = handle_example_command(text)
    else:
        response_text = "Unknown command: {}".format(command)

    # Return the response to Slack
    response = make_response(response_text)
    response.headers["Content-type"] = "application/json"
    return response

# Define the function that handles the /example command
def handle_example_command(text):
    return "You entered: {}".format(text)

# Start the Slack app using the Flask app as a middleware
handler = SlackRequestHandler(slack_app)
@app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)

if __name__ == "__main__":
    app.run(debug=True)
