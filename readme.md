# Overview
This is a python daemon that runs in the background, monitoring a folder for new files.  When it detects a file it automatically encodes the video and uploads it to Vimeo.

- The original and encoded videos are stored in separate folders.
- If the process fails, a notification email is sent.
- The file must be unmodified for a short period before encoding will begin.  This allows slow uploads or recording directly to the directory.


## How to Install
```
git clone git@github.com:davidbartonau/vimeo-uploader.git

# Set up your config
cp uploader.conf /etc/vimeo-uploader.conf

vi /etc/vimeo-uploader.conf

# run in command line first so we can see its output, [do not as service yet]
python3 uploader.py /etc/vimeo-uploader.conf
```

## Prerequisites
```
# Need to install the following for vimeo python api
sudo apt install libssl-dev
sudo apt install libcurl4-openssl-dev
sudo apt install python3-pip
```

### Not sure if we need this
```
python3 -m pip install --user virtualenv

# cd into uploader directory

python3 -m virtualenv env

# Install python dependencies

pip install -r requirements.txt

pip install PyVimeo
pip install pyyaml
```
## Run as a service
For start/boot settings, 
Need to edit the file 'upvimeo.service' to match your directory structure
and copy it to '/etc/systemd/system'

then run command
```
sudo systemctl daemon-reload
sudo systemctl enable upvimeo.service
sudo systemctl start upvimeo
```
