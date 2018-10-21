import vimeo
import asyncio
import os
import shutil
import sys
import time
import re
import subprocess
from uuid import uuid4
import logging
# Import smtplib for the actual sending function
import smtplib
import yaml

# Import the email modules we'll need
from email.message import EmailMessage


# Need to change this to point to conf file. e.g /etc/uploader.conf
SETTINGS_FILE = './uploader.conf'

TEST_MODE = False

# Custom exception/error classes
class SettingsFileNotFound(Exception):
    pass


class CannotConvertVideoFile(Exception):
    pass


class CannotUploadVideoFile(Exception):
    pass


class InvalidCredentialsError(Exception):
    pass


class Uploader:

    def __init__(self, settings_file):
        logging.info('Initialising from settings: ' + settings_file)

        if not os.path.exists(settings_file):
            raise SettingsFileNotFound()

        with open(settings_file, 'rt') as y:
            settings = yaml.load(y)

            self.CLIENT_ID = settings.get('client_id', '')
            self.CLIENT_SECRET = settings.get('client_secret', '')
            self.CLIENT_ACCESS_TOKEN = settings.get('client_access_token', '')

            self.EMAIL_USER = settings.get('email_user', '')
            self.EMAIL_PASSWORD = settings.get('email_password', '')
            self.REPORT_EMAIL = settings.get('email_address', '')
            self.SMTP_SERVER = settings.get('smtp_server', '')
            self.SMTP_PORT = settings.get('smtp_port', 0)

            self.ENCODER = settings.get('encoder', '')
            self.OUTPUT_EXT = settings.get('output_ext', '')
            self.PRESET = settings.get('preset', '')

            self.MONITOR_FOLDER = settings.get('monitor_folder', '')
            self.UNPROCESSED = settings.get('unprocessed_folder', '')
            self.PROCESSED = settings.get('processed_folder', '')
            self.UPLOADED = settings.get('uploaded_folder', '')
            self.ORIGINALS = settings.get('originals_folder', '')
            # Number of seconds to wait before processing the file.
            # This is a simple check to determine if the we are done recording.
            # A video file modified within less that a second means that it is currently being edited/recorded
            self.UPLOAD_DELAY = settings.get('upload_delay', 5)

        self.v = vimeo.VimeoClient(
            token=self.CLIENT_ACCESS_TOKEN,
            key=self.CLIENT_ID,
            secret=self.CLIENT_SECRET
        )

        os.makedirs(self.UNPROCESSED, exist_ok=True)
        os.makedirs(self.PROCESSED, exist_ok=True)
        os.makedirs(self.UPLOADED, exist_ok=True)
        os.makedirs(self.ORIGINALS, exist_ok=True)

    def __get_encoder_command(self, input_file, output_file):
        return [
            a.replace(
                '{input_file}', input_file).replace(
                    '{output_file}', output_file).replace(
                        '{preset}', self.PRESET) for a in self.ENCODER.split(' ') if a and a != '']

    def __check(self):
        if self.CLIENT_ACCESS_TOKEN == '' or \
                self.CLIENT_SECRET == '' or \
                self.CLIENT_ID == '':

            raise InvalidCredentialsError()

    async def copy_file(self, source, destination):
        try:
            # If the file is present in the destination,
            # Delete it first
            logging.info('Copying file from {} to {}'.format(
                source, destination))
            if os.path.exists(destination):
                os.remove(destination)

            shutil.copyfile(source, destination)
            return destination
        except:
            pass

    async def move_file(self, source, destination):
        try:
            # If the file is present in the destination,
            # Delete it first
            logging.info('Moving file from {} to {}'.format(
                source, destination))
            if os.path.exists(destination):
                os.remove(destination)

            os.rename(source, destination)
            return destination
        except:
            pass

    def __can_email(self):
        return self.EMAIL_PASSWORD and self.EMAIL_USER and \
            self.REPORT_EMAIL and self.SMTP_SERVER and \
            self.SMTP_PORT > 0

    async def send_email(self, subject, message):
        if TEST_MODE:
            logging.info("Email sent: {}".format(message))
            return

        if not self.__can_email():
            logging.warning('Cannot send email. No email credentials found.')
            return

        try:
            logging.info('Sending email message \"{}\" to \"{}\"'.format(
                message, self.REPORT_EMAIL))
            msg = EmailMessage()
            msg.set_content(message)
            msg['subject'] = subject
            msg['From'] = self.EMAIL_USER
            msg['To'] = self.REPORT_EMAIL

            # Send the message via our own SMTP server.
            s = smtplib.SMTP_SSL(self.SMTP_SERVER, self.SMTP_PORT)
            s.ehlo()
            s.login(self.EMAIL_USER, self.EMAIL_PASSWORD)
            s.send_message(msg)
            s.quit()
        except:
            pass

    async def convert(self, source_video):

        logging.info('Converting video: ' + source_video)

        basename = os.path.basename(source_video)
        fname, ext = os.path.splitext(basename)

        destination_if_success = os.path.join(
            self.PROCESSED, fname + self.OUTPUT_EXT)
        if os.path.exists(destination_if_success):
            os.remove(destination_if_success)

        completed_proc = subprocess.run(
            self.__get_encoder_command(source_video, destination_if_success)
        )

        # Do convert, if success
        # return await self.move_file(source_video, destination_if_success)
        # Else

        # If the file is not in the destination,
        # it means it was not converted, therefore we move it to unprocess folder
        if not os.path.exists(destination_if_success):
            logging.error('Cannot convert file: ' + source_video)
            await self.move_file(source_video, os.path.join(self.UNPROCESSED, basename))
        else:
            return await self.move_file(source_video, destination_if_success)

    async def upload(self, source_video):
        title = os.path.basename(source_video)
        logging.info('Uploading video: \"{}\"'.format(source_video))
        try:
            r = self.v.upload(source_video, data={
                              'name': title, 'description': title})
            # If success
            # Move the file to uploaded folder
            basename = os.path.basename(source_video)
            destination = os.path.join(self.UPLOADED, basename)
            d = await self.move_file(source_video, destination)
            return d
        except Exception as e:
            logging.error('Video was not uploaded [{}]'.format(source_video))
            logging.error('Reason: ' + str(e))

    async def last_modified(self, original):
        last_mod = os.path.getmtime(original)
        now_time = time.time()
        return now_time - last_mod

    async def run(self):

        logging.info('Running Vimeo uploader.')
        logging.info('Monitoring folder: {}'.format(
            os.path.abspath(self.MONITOR_FOLDER)))

        self.__check()

        while True:
            try:
                logging.info('I am alive !')
                await asyncio.sleep(1)
                # list all files inside the MONITOR_FOLDER directory
                for f in os.listdir(self.MONITOR_FOLDER):
                    fname, ext = os.path.splitext(f)
                    # Support only the following video file types
                    if not ext in ['.ogv', '.mkv', '.mp4']:
                        continue

                    logging.info('found file: %s' % (fname, ))
                    original = os.path.join(self.MONITOR_FOLDER, f)

                    past_seconds = await self.last_modified(original)
                    if past_seconds < self.UPLOAD_DELAY:
                        logging.info(
                            'Waiting to complete recording of {}. Time left is {:.0f} sec/s: '.format(
                                f, self.UPLOAD_DELAY - past_seconds)
                        )
                        continue

                    await self.copy_file(original, os.path.join(
                        self.ORIGINALS, os.path.basename(original)))

                    converted = await self.convert(original)
                    if not converted:
                        await self.send_email(
                            "VIMEO VIDEO NOT CONVERTED",
                            'A video with filename {} was not converted'.format(
                                f)
                        )
                        continue

                    UPLOADED = await self.upload(converted)
                    if not UPLOADED:
                        await self.send_email(
                            "VIMEO - VIDEO NOT UPLOADED",
                            'A video with filename {} was not UPLOADED'.format(
                                f)
                        )
                        continue

                    logging.info(
                        'Video \"{}\" successfully UPLOADED.'.format(f))
            except Exception as ex:
                logging.warning('Loop error.\n' + str(ex))


if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    try:
        if len(sys.argv) > 1:
            uploader = Uploader(sys.argv[1])
        else:
            uploader = Uploader(SETTINGS_FILE)

        loop = asyncio.get_event_loop()
        loop.run_until_complete(uploader.run())
    except SettingsFileNotFound:
        logging.warning('Settings file not found!')
    except KeyboardInterrupt:
        logging.warning('Program interrupted by user [KeyboardInterrupt]')
    except Exception as ee:
        logging.warning('Main error')
        uploader.send_email(
            "VIMEO UPLOADER",
            'Main program ended with reason\n' + str(ee)
        )
