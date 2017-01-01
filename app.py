import tweepy
import config
import logging
import shelve
import time
# from collections import OrderedDict
logging.basicConfig(filename='archiver.log',
                    level=getattr(logging, config.LOG_LEVEL))

AUTH = tweepy.OAuthHandler(config.API_KEY, config.API_SECRET)
AUTH.set_access_token(config.ACCESS_TOKEN, config.ACCESS_KEY)
API = tweepy.API(auth_handler=AUTH)


class StreamListener(tweepy.StreamListener):
    def __init__(self, store, *args, **kwargs):
        self._store = store
        super(StreamListener, self).__init__(*args, **kwargs)

    def on_status(self, status):
        # write each status in a new file
        # write each attached image in a new file
        print status.text
        TweetStore(self._store, user=status.user).add(status)

    def on_error(self, status_code):
        print "error from twitter API {}".format(status_code)
        time.sleep(2)
        return True


class TweetStore(object):

    def __init__(self, shelf, user, tweets=None, api=None):
        assert isinstance(user, tweepy.models.User)
        self._tweets = shelf.get(str(user.id_str), [])
        if tweets:
            assert isinstance(tweets, tweepy.models.ResultSet)
            self._tweets |= tweets.reverse()
        self._user = user
        self._store = shelf
        self.api = api
        self._user = user

    def save(self):
        self._store[str(self._user.id_str)] = self._tweets

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


if __name__ == '__main__':
    shelf = shelve.open('user_tweets_store.shelf')
    listener = StreamListener(shelf)
    streamer = tweepy.Stream(auth=AUTH,
                             listener=listener)
    user_ids_to_follow = []
    for screen_name in config.SCREEN_NAMES_TO_FOLLOW:
        user = API.get_user(screen_name)
        TweetStore(user=user, shelf=shelf, api=API).update()
        user_ids_to_follow.append(user.id_str)
    print "following IDs: " + ", ".join(user_ids_to_follow)
    print "Listening for statuses"
    streamer.filter(follow=user_ids_to_follow, async=True)
