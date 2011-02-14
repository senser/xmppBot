"""Extract data from Zenoss RRD files."""

from Jabber.Plugins import Plugin
from Jabber.ZenAdapter import ZenAdapter
from Jabber.Options import Options
from optparse import OptionError

class Data(Plugin):

    name = 'data'
    capabilities = ['data', 'info', 'help']

    def call(self, args, log, **kw):
#Dirty hack to make it work with multiword options (they must be in '' or "")
        i=-1
        appnd=False
        args1=[]
        for arg in args:
            if appnd:
                args1[i]+=' '+arg.replace("'",'').replace('"','')
            else:
                i+=1
                args1.append(arg.replace("'",'').replace('"',''))
            if arg[0] in ('"', "'"): appnd=True
            if arg[-1] in ('"', "'"): appnd=False
        args=args1

        log.debug('Data extraction plugin running with arguments %s' % args)

        opts = self.options()

        adapter = ZenAdapter()
        try:
            (options, arguments) = opts.parse_args(args)
            log.debug('Done parsing arguments.  Options are "%s", arguments expanded to %s' % (options, arguments))
        except OptionError, message:
            return str(message)
        if options.deviceName is None or (not options.list and options.dataPointName is None):
            return 'NO.  You must specify both device and datapoint with -d and -p.'

        devices = adapter.devices(options.deviceName)
        if len(devices) == 0:
            return 'Cannot find a device, ip or mac for "%s"' % options.deviceName
        log.debug('Found %d devices matching %s' % (len(devices), devices))
        if options.list:
            dataPoints = {}
            if options.subComponent:
                for device in devices:
                    componentList = adapter.components(device, options.subComponent)
                    if componentList:
                        for component in componentList:
                            for validPoint in component.getRRDDataPoints():
                                dataPoints[validPoint.id] = '_'.join([ pathTuple[1] for pathTuple in validPoint.breadCrumbs()])
            else:
                for device in devices:
                    for validPoint in device.getRRDDataPoints():
                        dataPoints[validPoint.id] = '_'.join([ pathTuple[1] for pathTuple in validPoint.breadCrumbs()])
            message = 'Valid datapoints:\n'
            for name, path in dataPoints.iteritems():
                message += '%s (%s)\n' % (name, path)
            return message
        log.debug('Going to look for datapoint %s' % options.dataPointName)
        # rrdtool cannot accept arguments in unicode, so convert dataPointName to ascii first
        message = self.obtainValues(adapter, devices, options.dataPointName.encode('ascii', 'ignore'), options.subComponent, log)
        return message

    def subDevices(self, device):
        return device.getSubObjects()

    def obtainValues(self, adapter, devices, dataPoint, component, log):
        message = ''
        log.debug('Have %d devices to check for %s' % (len(devices), dataPoint))
        for device in devices:
            log.debug('Checking %s. For the dataPoint %s' % (device.id, dataPoint))
            # try to get it directly from the device first.
            if self.hasDataPoint(device, dataPoint):
                log.debug('The device %s does have the dataPoint %s' % (device, dataPoint))
                value = device.getRRDValue(dataPoint)
                message += '%s: %s\n' % (device.id, value)
            elif component is not None:
                compList = adapter.components(device, component)
                if not compList:
                    return 'Sorry.  Cannot find a component %s on %s' % (component, device)
                if len(compList)>1:
                    return 'Multiple components found. Please, define more exaclty.'
                comp = compList[0]
                if self.hasDataPoint(comp, dataPoint):
                    value = comp.getRRDValue(dataPoint)
                    message += '%s %s: %s\n' % (device.name(), component, value)
                else:
                    message += '%s %s: Does not have a datapoint named %s.  Remember, spelling and case matter.  Try -l for a list of datapoint' % (device.name(), component, dataPoint)
            else:
                message += '%s: Unable to find the datapoint %s. Remember, spelling and case matter.  Try -l for a list of datapoints' % (device.name(), dataPoint)
        return message

    def hasDataPoint(self, entity, dataPoint):
        hasPoint = False
        for point in entity.getRRDDataPoints():
            if point.__name__ == dataPoint:
                hasPoint = True
                break
        return hasPoint

    def private(self):
        return False

        # parse the options
    def options(self):
        parser = Options(description = 'Retrieve latest value read from the device for datapoint.  Simple example:\n data -d 10.1.1.1 -p laLoadInt1', prog = 'data')
        parser.add_option('-d', '--device', dest='deviceName', help='Device name, IP or MAC.')
        parser.add_option('-p', '--point', dest='dataPointName', help='Acknowledge all events.  If -e is also specified, it will still acknowledge every event.')
        parser.add_option('-l', '--list', dest='list', action='store_true', help='Only list datapoints for the device and/or component.')
        parser.add_option('-s', '--subcomponent', dest='subComponent', help='Optional subcomponent name, if the datapoint does not reside directly on the device.  You will probably have to specify this.  Here are two usage example:\n  data -d buffalo.example.com -p usedBlocks -s filesystems\n data -10.1.1.1 -p ifInErrors -s interfaces')
        return parser

    def help(self):
        opts = self.options()
        return str(opts.help())
