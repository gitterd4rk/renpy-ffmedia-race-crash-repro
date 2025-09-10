# Minimal RenPy script for media_read_video race condition reproduction

define video_assets = [
    "videos/clip01.webm",
    "videos/clip02.webm", 
    "videos/clip03.webm",
    "videos/clip04.webm",
    "videos/clip05.webm",
    "videos/clip06.webm",
    "videos/clip07.webm",
    "videos/clip08.webm"
]

init python:
    import random
    import gc
    
    def memory_pressure():
        dummy_data = [b'x' * 1024 for i in range(100)]
        del dummy_data
        gc.collect()
    
    def rapid_transition():
        memory_pressure()
        selected_video = random.choice(video_assets)
        try:
            renpy.movie_cutscene(selected_video, delay=0.001)
        except:
            pass

label start:
    $ _skipping = True
    $ preferences.skip_unseen = True
    
    label reproduction_loop:
        $ rapid_transition()
        jump reproduction_loop