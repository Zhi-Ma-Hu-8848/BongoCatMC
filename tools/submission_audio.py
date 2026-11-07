"""NetEase error 33: actual Ogg Vorbis audio with bitrate <= 128 kbps."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile

import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
AUDIO_SUFFIXES = {'.wav', '.ogg', '.mp3', '.flac', '.aac', '.m4a', '.opus', '.wma'}


def vorbis_info(path):
    path = Path(path)
    raw = path.read_bytes()
    marker = raw.find(b'\x01vorbis', 0, 4096)
    if path.suffix.lower() != '.ogg' or raw[:4] != b'OggS' or marker < 0 or len(raw) < marker + 30:
        raise ValueError('Expected .ogg containing Vorbis audio: ' + str(path))
    version, channels, rate, maximum, nominal, minimum = struct.unpack_from('<IBIiii', raw, marker + 7)
    if version != 0 or channels < 1 or rate < 1 or not 0 < nominal <= 128000 or maximum > 128000 or minimum > 128000:
        raise ValueError('Invalid Vorbis header / bitrate exceeds 128 kbps: ' + str(path))
    info = sf.info(path)
    if info.format != 'OGG' or info.subtype != 'VORBIS' or info.frames <= 0:
        raise ValueError('Invalid or empty Ogg Vorbis stream: ' + str(path))
    return {'channels': channels, 'rate': rate, 'bitrate': nominal,
            'maximum_bitrate': maximum, 'frames': info.frames, 'seconds': info.duration}


def write_audio(source, output):
    """Encode from the original source, never from an earlier lossy output."""
    import imageio_ffmpeg
    source, output = Path(source).resolve(), Path(output).resolve()
    if output.suffix != '.ogg' or source == output:
        raise ValueError('Use a separate .ogg output file.')
    # MP3 header duration can include metadata/padding; compare decoded samples.
    samples, source_rate = sf.read(source, dtype='float32', always_2d=True)
    source_channels = samples.shape[1]
    source_duration = len(samples) / source_rate
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='bongocat-audio-', dir=output.parent) as temp:
        candidate = Path(temp) / output.name
        subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-v', 'error', '-nostdin',
                        '-i', str(source), '-map', '0:a:0', '-vn', '-map_metadata', '-1',
                        '-c:a', 'libvorbis', '-b:a', '96k', '-maxrate:a', '128k',
                        str(candidate)], check=True, capture_output=True, timeout=60)
        result = vorbis_info(candidate)
        if (result['rate'], result['channels']) != (source_rate, source_channels):
            raise ValueError('Encoder changed sample rate or channels.')
        if abs(result['seconds'] - source_duration) > .02:
            raise ValueError('Encoder changed audio duration.')
        candidate.replace(output)
    # Only remove the generated sibling WAV after its replacement passes checks.
    legacy = output.with_suffix('.wav')
    if legacy != source and legacy.is_file():
        legacy.unlink()
    return result


def check_audio(resource_pack):
    resource_pack = Path(resource_pack)
    found = {}
    for path in sorted((resource_pack / 'sounds').rglob('*')):
        if path.is_file() and path.suffix.lower() in AUDIO_SUFFIXES:
            found[path.relative_to(resource_pack).as_posix()] = vorbis_info(path)
    data = json.loads((resource_pack / 'sounds/sound_definitions.json').read_text(encoding='utf-8-sig'))
    for event, definition in data.get('sound_definitions', data).items():
        if not isinstance(definition, dict):
            continue
        for entry in definition.get('sounds', []):
            name = entry if isinstance(entry, str) else entry['name']
            if name + '.ogg' not in found:
                raise ValueError('Sound definition has no validated audio: %s -> %s' % (event, name))
    return found


def rebuild():
    rp = ROOT / 'addon/resource_pack'
    target = rp / 'sounds/bongocatmc'
    write_audio(ROOT / 'assets/source/standard/live2d_motion1.flac', target / 'lightning.ogg')
    source = ROOT / 'assets/source/deepseek/img/standard/cat_model'
    config = json.loads((source / 'deepseek.model3.json').read_text(encoding='utf8'))
    for clip in config['FileReferences']['Motions']['CAT_motion_lock']:
        if clip.get('Sound'):
            name = 'deepseek_' + clip['File'].split('.')[0].lower()
            write_audio(source / clip['Sound'], target / (name + '.ogg'))
    return check_audio(rp)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--rebuild', action='store_true', help='Rebuild the three known effects from original sources')
    args = parser.parse_args()
    result = rebuild() if args.rebuild else check_audio(ROOT / 'addon/resource_pack')
    print(json.dumps(result, ensure_ascii=False, indent=2))
