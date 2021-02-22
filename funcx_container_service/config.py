class DefaultConfig(object):
    DEBUG = False
    TESTING = False


class TestConfig(DefaultConfig):
    TESTING = True


class DebugConfig(DefaultConfig):
    DEBUG = True
