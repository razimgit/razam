import librosa
import os
import pickle
import numpy as np
import multiprocessing as mp
import scipy.ndimage as ndimage
from scipy.ndimage.filters import maximum_filter
from audioread import NoBackendError

NEIGHBORHOOD_SIZE = 20
SAMPLE_RATE = 22050
CPUs = 4

def get_list_of_files(dir_path, recursive=False):
    files = []
    with os.scandir(dir_path) as entries:
        for entry in entries:
            if recursive and entry.is_dir():
                files.extend(get_list_of_files(entry, recursive=True))
            elif entry.is_file():
                files.append(entry.path)
    return files


def load_and_resample(audiofile_path, sample_rate=SAMPLE_RATE):
    import audioread
    '''Loads and resamples audio file
    Returns a (audiofile_path, time_series) tuple'''
    try:
        ts, _ = librosa.load(audiofile_path, sr=sample_rate, res_type='kaiser_fast')
    except NoBackendError:
        print(f'Could not load {audiofile_path} as audio')
        return None
    return (audiofile_path, ts)


def load_and_resample_dir(dir_path, recursive=False):
    '''Loads and resamples audio files given in dir_path
    Returns a list of (audio_path, time_series) tuples'''
    files = get_list_of_files(dir_path, recursive)
    ts_collection = [tup for file in files if (tup := load_and_resample(file)) is not None]
    return ts_collection


def build_constellation_index(constellation_collection, multiprocess=False, pool=None):
    '''If multiprocess == True, multiprocessing.Pool must be provided'''
    result_index = {}
    if multiprocess:
        hashes_collection = [pool.apply(get_hashes, args=(name, con)) for (name, con) in constellation_collection]
        result_index = {k:v for element in hashes_collection for k,v in element.items()}
    else:
        for name, con in constellation_collection:
            hashes = get_hashes(name, con)
            result_index.update(hashes)
    return result_index


def get_hashes(name, constellation):
    hashes = {}
    for i, (t1, f1) in enumerate(constellation):
        # My target zone is considered to be 40 points around the anchor point
        target_points = constellation[i-20 : i+20]
        for t2, f2 in target_points:
            dt = t2 - t1
            hashes.setdefault((f1, f2, dt), []).append((t1, name))
    return hashes


def form_constellation(ts, sample_rate=SAMPLE_RATE):
    '''ts -- a single time series'''
    S = librosa.feature.melspectrogram(ts, sr=sample_rate, n_mels=256, fmax=4000)
    S = librosa.power_to_db(S, ref=np.max)
    # get local maxima
    Sb = maximum_filter(S, NEIGHBORHOOD_SIZE) == S
    
    Sbd, num_objects = ndimage.label(Sb)
    objs = ndimage.find_objects(Sbd)
    points = []
    for dy, dx in objs:
        x_center = (dx.start + dx.stop - 1) // 2
        y_center = (dy.start + dy.stop - 1) // 2    
        if (dx.stop - dx.start) * (dy.stop - dy.start) == 1:
            points.append((x_center, y_center))
    return sorted(points)


def get_offset_diffs(sample, index):
    offset_diffs = {}

    for key, value in sample.items():
        if key in index:
            for sample_offset, _ in value:
                for db_offset, name in index[key]:
                    offset_diffs.setdefault(name, []).append(db_offset - sample_offset)
    return offset_diffs


def get_best_matches(offset_diffs):
    binwidth = 150
    max_matches = []

    for name, diffs in offset_diffs.items():
        hist, _ = np.histogram(diffs, bins=range(min(diffs), max(diffs) + binwidth, binwidth))
        m = np.max(hist)
        max_matches.append((name, m))
    best_matches = sorted(max_matches, key=lambda x: x[1], reverse=True)

    return [path for path, _ in best_matches]


def path_and_constellation(path_ts):
    path, ts = path_ts
    return (path, form_constellation(ts))


def create_index(path, recursive=False, multiprocess=False):
    if os.path.isfile(path):
        ts_coll = [load_and_resample(path)]
    elif os.path.isdir(path):
        ts_coll = load_and_resample_dir(path, recursive)

    if multiprocess:
        pool = mp.Pool(CPUs)
        constellations = [pool.apply(path_and_constellation, args=(path_ts,)) for path_ts in ts_coll]
        index = build_constellation_index(constellations, multiprocess, pool)
        pool.close()
    else:
        constellations = [(path, form_constellation(ts)) for path, ts in ts_coll]
        index = build_constellation_index(constellations)
    return index


def update_index(index, dir_path_or_files):
    if isinstance((files := dir_path_or_files), tuple):
        for file in files:
            index.update(create_index(file))
    elif os.path.isdir(dir_path := dir_path_or_files):
        new_index = create_index(dir_path)
        index.update(new_index)


def open_index_file(index_filename):
    if os.path.exists(index_filename):    
        with open(index_filename, 'rb') as file:
                index = pickle.load(file)
        return index
    else:
        return None


def save_index_file(index, index_filename):
    with open(index_filename, 'wb') as file:
        pickle.dump(index, file)