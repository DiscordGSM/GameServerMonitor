import asyncio
import os
import site
import sys

import servicemanager
import win32service

# Fix ValueError: set_wakeup_fd only works in main thread
if sys.platform == 'win32' and (3, 8, 0) <= sys.version_info < (3, 9, 0):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Add virtual env site-packages
path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
venv = os.getenv('VIRTUAL_ENV', os.path.join(path, 'venv'))
site.addsitedir(os.path.join(venv, 'Lib', 'site-packages'))

import win32serviceutil  # noqa: E402

# Set working directory
os.chdir(path)

from discordgsm import client  # noqa: E402


class WindowsService(win32serviceutil.ServiceFramework):
    _svc_name_ = os.getenv('SERVICE_NAME', 'DgsmSvc')
    _svc_display_name_ = os.getenv('SERVICE_DISPLAY_NAME', 'DiscordGSM Service')
    _svc_description_ = os.getenv('SERVICE_DESCRIPTION', 'A discord bot that monitors your game server and tracks the live data of your game servers.')

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)

    def SvcStop(self):
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)

        try:
            # Please submit a pull request on github if you have a better solution thanks
            asyncio.run(client.close())
        except RuntimeError:
            # RuntimeError: got Future <Future pending> attached to a different loop
            pass

    def SvcDoRun(self):
        servicemanager.LogMsg(servicemanager.EVENTLOG_INFORMATION_TYPE, servicemanager.PYS_SERVICE_STARTED, (self._svc_name_, ''))
        client.run(os.environ['APP_TOKEN'])


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(WindowsService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(WindowsService)
