import os
from pathlib import Path


def vlc_encode(video, vlc_out):
    return os.system(f'ffmpeg -y -i {video} -c:v libx264 -coder vlc {vlc_out}') == 0


def main():
    video_folder = Path('/Users/jusbin/Movies/v')
    vlc_out_folder = video_folder.parent / 'vlc'
    bac_out_folder = video_folder.parent / 'bac'
    vlc_out_folder.mkdir(parents=True, exist_ok=True)
    bac_out_folder.mkdir(parents=True, exist_ok=True)

    for video in video_folder.glob('*.y4m'):
        vlc_out = vlc_out_folder / (video.stem + '.h264')
        bac_out = bac_out_folder / (video.stem + '.h264')
        vlc_encode(video, vlc_out)
        print(f'vlc encode {video} to {vlc_out}:' + (' success' if vlc_out.exists() else ' failed'))
        # bac_encode(video, bac_out)


if __name__ == '__main__':
    main()