import os
import re
import subprocess

from jinja2 import Template

from mtp_transaction_uploader import settings

if __name__ == '__main__':
    # collect environment variables
    re_env_name = re.compile(r'^[A-Z_]+$')
    environment_variables = [
        (param, getattr(settings, param))
        for param in dir(settings)
        if re_env_name.match(param)
    ]

    # write crontab file from template
    this_dir = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(this_dir, 'crontab.jinja')) as f:
        crontab_template = Template(f.read())
    crontab_contents = crontab_template.render(params=environment_variables)
    crontab_file = os.path.join(this_dir, 'transaction-uploader.cron')
    with open(crontab_file, 'w+') as f:
        f.write(crontab_contents)

    # install crontab
    subprocess.check_call(['crontab', '-u', 'root', 'transaction-uploader.cron'])
    subprocess.check_call(['cron'])
    os.remove(crontab_file)
