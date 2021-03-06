# Copyright (c) 2016 Ansible, Inc.
# All Rights Reserved.

import time
import logging
from slackclient import SlackClient

from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from awx.main.notifications.base import AWXBaseEmailBackend

logger = logging.getLogger('awx.main.notifications.slack_backend')
WEBSOCKET_TIMEOUT = 30


class SlackBackend(AWXBaseEmailBackend):

    init_parameters = {"token": {"label": "Token", "type": "password"},
                       "channels": {"label": "Destination Channels", "type": "list"}}
    recipient_parameter = "channels"
    sender_parameter = None

    def __init__(self, token, fail_silently=False, **kwargs):
        super(SlackBackend, self).__init__(fail_silently=fail_silently)
        self.token = token
        self.connection = None

    def open(self):
        if self.connection is not None:
            return False
        self.connection = SlackClient(self.token)
        if not self.connection.rtm_connect():
            if not self.fail_silently:
                raise Exception("Slack Notification Token is invalid")

        start = time.time()
        time.clock()
        elapsed = 0
        while elapsed < WEBSOCKET_TIMEOUT:
            events = self.connection.rtm_read()
            if any(event['type'] == 'hello' for event in events):
                return True
            elapsed = time.time() - start
            time.sleep(0.5)

        raise RuntimeError("Slack Notification unable to establish websocket connection after {} seconds".format(WEBSOCKET_TIMEOUT))

    def close(self):
        if self.connection is None:
            return
        self.connection = None

    def send_messages(self, messages):
        if self.connection is None:
            self.open()
        sent_messages = 0
        for m in messages:
            try:
                for r in m.recipients():
                    if r.startswith('#'):
                        r = r[1:]
                    self.connection.rtm_send_message(r, m.subject)
                    sent_messages += 1
            except Exception as e:
                logger.error(smart_text(_("Exception sending messages: {}").format(e)))
                if not self.fail_silently:
                    raise
        return sent_messages
