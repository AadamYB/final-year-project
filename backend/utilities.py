""" Utilities script - to be adopted later?? """

class Counter:
    """ Counter class that can be used as a context manager/decorator/class object """
    counts = {}

    def __init__(self, label="default"):
        self.label = label
        if label not in Counter.counts:
            Counter.counts[label] = 0

    def increment(self):
        Counter.counts[self.label] += 1
        return Counter.counts[self.label]

    def __enter__(self):
        self.increment()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __call__(self, func):
        def wrapper(*args, **kwargs):
            self.increment()
            return func(*args, **kwargs)
        return wrapper

    @classmethod
    def get_counts(cls):
        return dict(cls.counts)