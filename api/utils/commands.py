import math
import random
import sys

def get_random_words(word_list: list[str], length: int, add_new_lines: bool = False) -> list[str]:
    words = []
    for i in range(length):
        words.append(random.choice(word_list))
        if add_new_lines:
            if random.randint(0, 10) == 0:
                words.append('\n\n')
    return words

def print_progress(on: int, outof: int, decimal_places=0, show_values=False):
    progress = on / outof
    progress *= 100
    modifier = 1
    for _ in range(decimal_places):
        modifier *= 10
    progress = math.floor(progress * modifier) / modifier
    progress_str = str(progress)
    split = progress_str.split('.')
    before_decimal = split[0]
    after_decimal = split[1]
    after_decimal = after_decimal.ljust(decimal_places, '0')
    if decimal_places == 0:
        progress_str = before_decimal
    else:
        progress_str = f'{before_decimal}.{after_decimal}'
    sys.stdout.write(f"  {f'{on}/{outof} ' if show_values else ''}Progress: {progress_str}%\r")

def populate_words():
    words = []
    filepath = "api/management/commands/data/words.txt"
    with open(filepath, "r") as file:
        txt = file.read()
        words = txt.split('\n')
    return [w for w in words if w != '']
