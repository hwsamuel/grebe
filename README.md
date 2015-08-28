Twitter monitor for retrieving Alberta-related tweets from live Twitter Stream and Twitter Search APIs and saving into MongoDB database.

The Twitter API requires consumer and access token keys. To set up your keys, use your Twitter account and follow the [instructions](http://iag.me/socialmedia/how-to-create-a-twitter-app-in-8-easy-steps/). Afterwards, edit the source file to enter your tokens in `grebe_lib.py`.

To set up MongoDB, please see the appropriate [documentation](http://docs.mongodb.org/manual).

The code has three main components: a [Flask](http://flask.pocoo.org/) web application, a Stream API script, `grebe_stream.py` and a Search API script, `grebe_search.py`. 

To run the Search or Stream API script, call each separately from the command prompt, e.g. `python grebe_search.py`. The scripts monitor the respective Twitter APIs and store the appropriate tweets into MongoDB. 

The Flask web application provides a web interface for some analytics based on the stored tweets. To run the Flask app, use `python grebe.py` and then go to your web browser at [http://127.0.0.1:5000](http://127.0.0.1:5000).