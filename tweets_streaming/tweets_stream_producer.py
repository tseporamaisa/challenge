import tweepy
import json
import time
import boto3
from decouple import config


class CustomStreamListener(tweepy.StreamListener):
    """
    Class inherits from tweepy.StreamListener and overides the on_status method.
    on_status sends streamed tweets to Kinesis Firehose
    """

    def __init__(self, kinesis_client, stream_name, time_limit):
        self.start_time = time.time()
        self.limit = time_limit
        self.kinesis_client = kinesis_client
        self.stream_name = stream_name
        super(CustomStreamListener, self).__init__()

    def on_connect(self):
        print("Connected to Twitter API.")

    def on_status(self, status):
        # exclude retweets
        if not hasattr(status, "retweeted_status"):
            tweet_data = status._json
            self.send_data_to_kinesis(data=tweet_data)

        if (time.time() - self.start_time) > self.limit:
            return False

    def on_error(self, status_code):
        if status_code == 420:
            # On stream disconect returnng True immediately reconnects
            return True

    def send_data_to_kinesis(self, data):
        self.kinesis_client.put_record(StreamName=self.stream_name,
                                       Data=json.dumps(data),
                                       PartitionKey="TwitterPartition")


def main(streaming_duration=3600, key_words_to_track="EasyEquities"):
    """
    Initiate tweets stream and send to kinesis firehose

    Parameters
    ----------
    streaming_duration : int, optional
        duration of streaming data, by default 3600
    key_words_to_track : str, optional
        comma separated list of keywords to used to filter tweets, by default "EasyEquities"
    """

    api_key = config('TWITTER_API_KEY')
    api_secret_key = config('TWITTER_API_SECRET_KEY')
    access_token = config('TWITTER_ACCESS_TOKEN')
    access_token_secret = config('TWITTER_ACCESS_TOKEN_SECRET')

    # authenticate Twitter client
    authentication = tweepy.OAuthHandler(api_key, api_secret_key)
    authentication.set_access_token(access_token, access_token_secret)
    api = tweepy.API(authentication)

    kinesis_client = boto3.client('kinesis')
    stream_name = "TwitterStream"

    streamListener = CustomStreamListener(kinesis_client=kinesis_client,
                                          stream_name=stream_name,
                                          time_limit=streaming_duration)

    myStream = tweepy.Stream(auth=api.auth, listener=streamListener,
                             tweet_mode="extended")

    key_words = key_words_to_track.split()

    myStream.filter(track=key_words, is_async=True)


if __name__ == '__main__':
    key_words = config('KEY_WORDS_TO_TRACK')

    duration = int(config('STREAM_DURATION'))

    main(key_words_to_track=key_words, streaming_duration=duration)
