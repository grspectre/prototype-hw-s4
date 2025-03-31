import multiprocessing
import time
import random
import string
import itertools
import hashlib


def get_hash(data: str) -> str:
    return hashlib.md5(data.encode("utf8")).hexdigest()


def worker(input_queue, output_queue, stop_event, hashes):
    while not stop_event.is_set():
        try:
            data = input_queue.get(timeout=1)
            if data is None:
                print(f"{multiprocessing.current_process().name} data is None")
                break
            h = get_hash(data)
            for inp_hash in hashes:
                if h == inp_hash:
                    print(f'Процесс {multiprocessing.current_process().name} нашёл хэш!')
                    output_queue.put(f"{data}:{inp_hash}")
        except Exception as e:
            print(f'Ошибка: {str(e)}.')


def generate_sequence():
    symbols = string.digits + string.ascii_lowercase + string.ascii_uppercase
    for sequence in itertools.product(symbols, repeat=6):
        yield ''.join(sequence)


def brute_force(hash: str):
    num_workers = multiprocessing.cpu_count()
    input_queue = multiprocessing.Queue()
    output_queue = multiprocessing.Queue()
    stop_event = multiprocessing.Event()

    workers = []
    for _ in range(num_workers):
        p = multiprocessing.Process(target=worker, args=(input_queue, output_queue, stop_event, hash))
        p.start()
        workers.append(p)

    max_q = 1000000
    min_q = 50000
    for i in generate_sequence():
        input_queue.put(i)
        if input_queue.qsize() > max_q:
            print(f'sleep producing strings {i} {input_queue.qsize()}')
            while True:
                if input_queue.qsize() < min_q:
                    break
                time.sleep(0.2)
        if output_queue.qsize() > 0:
            data = output_queue.get()
            print(data)
            break

    for p in workers:
        p.join()
    for _ in workers:
        input_queue.put(None)
    print("Хост-процесс завершен.")


if __name__ == '__main__':
    hashes = [
        'b9e9e5e6bb679e91c43a229e9f21a37f', '20afc891efbd174d0cbb8f02bd49b587', '1a6de0f03d8c7578e4114ebc8c0f9fec'
    ]
    brute_force(hashes)
