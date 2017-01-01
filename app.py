import tweepy
import config
import logging
import shelve
import time
from contextlib import closing

# from collections import OrderedDict
logging.basicConfig(filename='archiver.log',
                    level=getattr(logging, config.LOG_LEVEL))

AUTH = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET)
AUTH.set_access_token(config.ACCESS_TOKEN, config.ACCESS_KEY)
API = tweepy.API(auth_handler=AUTH)


class StreamListener(tweepy.StreamListener):
    def __init__(self, store_path, *args, **kwargs):
        self._store_path = store_path
        super(StreamListener, self).__init__(*args, **kwargs)

    def on_status(self, status):
        # write each status in a new file
        # write each attached image in a new file
        print status.text
        TweetStore(self._store_path, user=status.user).add(status)

    def on_error(self, status_code):
        print "error from twitter API {}".format(status_code)
        time.sleep(2)
        return True


class TweetStore(object):

    def __init__(self, store_path, user, api=None):
        assert isinstance(user, tweepy.models.User)
        self._tweets = []
        self._user = user
        self._store_path = store_path
        self.api = api
        self._user = user

    def save(self):
        with closing(shelve.open(self._store_path)) as store:
            store[str(self._user.id_str)] = self._tweets

    def add(self, tweet):
        self._tweets.append(tweet)
        self.save()

    def update(self):
        new_tweets = self.api.user_timeline(
            user_id=self.user.id,
            since_id=self._tweets[-1].id if self._tweets else None
        )
        new_tweets.reverse()
        for _ in new_tweets:
            self.add(_)
        self.save()

    @property
    def tweets(self):
        return self._tweets

    @property
    def user(self):
        return self._user


def run():
    shelf_path = 'user_tweets_store.shelf'
    listener = StreamListener(shelf_path)
    streamer = tweepy.Stream(auth=AUTH,
                             listener=listener)
    user_ids_to_follow = []
    for screen_name in config.SCREEN_NAMES_TO_FOLLOW:
        user = API.get_user(screen_name)
        TweetStore(user=user, store_path=shelf_path, api=API).update()
        user_ids_to_follow.append(user.id_str)
    print "following IDs: " + ", ".join(user_ids_to_follow)
    print "Listening for statuses"
    streamer.filter(follow=user_ids_to_follow, async=True)

if __name__ == '__main__':
    run()
