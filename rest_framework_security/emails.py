import os
from email.mime.image import MIMEImage

from django.contrib.staticfiles import finders
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import loader


def add_email_attaches(email: EmailMultiAlternatives):
    for name, img in getattr(settings, 'EMAIL_ATTACHES', {}):
        path = os.path.join(settings.BASE_DIR, img)
        fp = open(path, 'rb')
        msg_image = MIMEImage(fp.read())
        fp.close()
        msg_image.add_header('Content-ID', '<' + name + '>')
        msg_image.add_header('X-Attachment-Id', name)
        msg_image.add_header('Content-Disposition', 'inline', filename=name)
        email.attach(msg_image)
    return email


class EmailBase:
    subject_template_name = None
    email_template_name = None
    html_email_template_name = None

    def __init__(self, user, connection=None, site_id=1):
        self.user = user
        self.connection = connection
        self.site_id = site_id

    def get_context(self):
        return {
            "user": self.user,
            "site_name": self.site_name,
        }

    @property
    def site_name(self):
        from django.contrib.sites.models import Site

        return Site.objects.get(pk=self.site_id).name

    @property
    def from_email(self):
        return settings.DEFAULT_FROM_EMAIL

    @property
    def to_email(self):
        return self.user.email

    def send(self):
        context = self.get_context()
        subject = loader.render_to_string(self.subject_template_name, context)
        subject = subject.replace("\n", "")
        body = loader.render_to_string(self.email_template_name, context)
        email_message = EmailMultiAlternatives(
            subject, body, self.from_email, [self.to_email], connection=self.connection
        )
        if self.html_email_template_name is not None:
            html_email = loader.render_to_string(self.html_email_template_name, context)
            email_message.attach_alternative(html_email, "text/html")
            add_email_attaches(email_message)
        email_message.send()
