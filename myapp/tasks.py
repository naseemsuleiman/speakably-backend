from django.core.management import call_command

def run_send_reminders():
    call_command('send_reminders')