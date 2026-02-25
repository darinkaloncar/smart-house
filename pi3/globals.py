import threading

batch_slow = []
publish_limit_slow = 4
publish_event_slow = threading.Event()

batch_fast = []
publish_event_fast = threading.Event()

counter_lock = threading.Lock()