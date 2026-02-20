import threading

batch = []
publish_counter = 0
publish_limit = 5

counter_lock = threading.Lock()
publish_event = threading.Event()