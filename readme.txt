# Need to install the following for vimeo python api

sudo apt install libssl-dev

sudo apt install libcurl4-openssl-dev

sudo apt install python3-pip

python3 -m pip install --user virtualenv

# cd into uploader directory

python3 -m virtualenv env

# Install python dependencies

pip install -r requirements.txt

pip install PyVimeo

# For start/boot settings, 
# Need to edit the file 'upvimeo.service' to match your directory structure
# and copy it to '/etc/systemd/system'

# then run command

sudo systemctl daemon-reload
sudo systemctl enable upvimeo.service
sudo systemctl start upvimeo

# or run in command line first so we can see its output, [do not as service yet]

python uploader.py


