import vimeo
import os
import sys
import subprocess
import time
from datetime import datetime, timedelta
import uuid

# Chage this settings ===================================================================
# =======================================================================================

access_token2 = 'e97ad346d2d8a7e849aa991b7f9534b6'
client_id2 = '09b45375e54312c19d52d8c07795830c0e4680cb'
client_secret2 = 'q2XRLP36tItFS9qKjf4QNFBxRE82m2w602TmTuAQYbRn3nEnsE8xwqcok9ztevRlaNyrJ+A0gqAHT5QtnepPiL+RFmTvXfLO4sAugSNWPbdWZzxCCkNKvVss3VQdsOHq'

recording_folder = os.path.abspath('/home/osboxes/Desktop/uploader/')

processed_folder = os.path.join(recording_folder, 'processed/')
uploaded_folder = os.path.join(recording_folder, 'uploaded/')
unprocessed_folder = os.path.join(recording_folder, 'unprocessed/')

# =========================================================================================
# =========================================================================================

wait_seconds_b4_upload = 15  # seconds


def main():
    os.makedirs(processed_folder, exist_ok=True)
    os.makedirs(uploaded_folder, exist_ok=True)
    os.makedirs(unprocessed_folder, exist_ok=True)

    v = vimeo.VimeoClient(
        token=access_token2,
        key=client_id2,
        secret=client_secret2
    )

    while True:

        time.sleep(5)

        print('Looking for files in {}'.format(
            os.path.abspath(recording_folder)))

        for vid in os.listdir(recording_folder):

            fullname = os.path.join(recording_folder, vid)
            fname, ext = os.path.splitext(vid)

            try:
                if ext in ['.mp4', '.mkv', '.avi', '.ogv']:
                    last_mod = os.path.getmtime(fullname)
                    now_time = time.time()

                    delta = now_time - last_mod
                    print(
                        'File {} was last modified in {} second(s)'.format(vid, delta))

                    if delta > wait_seconds_b4_upload:  # 1 minute

                        # Do convert
                        random = str(uuid.uuid4()).split('-')[0]

                        destination = os.path.join(
                            processed_folder, fname + '_' + random + '.mkv')

                        print("converting video from '{}'\n\tto '{}'".format(
                            fullname, destination))

                        subprocess.run(['HandBrakeCLI', '-i', fullname, '-o',
                                        destination, '-Z', "H.264 MKV 1080p30"])

                        if not os.path.exists(destination):
                            raise Exception()

                        os.remove(fullname)
                        try:
                            print('\nUploading video {}...'.format(vid))
                            r = v.upload(destination)
                        except Exception as e:
                            print('Unable to upload video.')
                            print(e)
                            continue

                        os.rename(destination, os.path.join(
                            uploaded_folder, os.path.basename(destination)))
                        print('done uploading ' + vid)

            except Exception as ex:
                print('Something went wrong while processing {}'.format(vid))
                print(ex)
                if os.path.exists(destination):
                    os.remove(fullname)
                else:
                    if os.path.exists(fullname):
                        os.rename(fullname, os.path.join(
                            unprocessed_folder, os.path.basename(destination)))

            finally:
                sys.stdout.flush()


if __name__ == '__main__':
    main()
