"""Restart Jabber bot"""

from Jabber.Plugins import Plugin
from Products.ZenUtils.Utils import binPath
from Products.Jobber.jobs import ShellCommandJob
from Products.ZenUtils.ZCmdBase import ZCmdBase


class Restart(Plugin):

    name = 'restart'
    capabilities = ['restart', 'reboot', 'help']

    def call(self, args, log, **kw):
        if args: return self.help()
        log.debug('Restart plugin running with arguments %s' % args)
        log.debug('Restarting...')
        try:
            cmd = ZCmdBase(noopts = True)
        except Exception, e:
            return str(e) + '\nYou need to manually restart me from Zenoss Web Interface.'
        cmd.dmd.JobManager.addJob(ShellCommandJob, [binPath('xmppBot'), 'restart'])
        return 'Restarting in a few seconds...'

    def private(self):
        return False

    def help(self):
        return """
    usage restart
        Restart Zenoss Jabber bot.  Takes no arguments.
    """
