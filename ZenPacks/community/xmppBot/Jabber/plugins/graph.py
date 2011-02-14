"""Extract graphs."""

from Jabber.Plugins import Plugin
from Jabber.ZenAdapter import ZenAdapter
from Jabber.Options import Options
from optparse import OptionError

class Graph(Plugin):

    name = 'graph'
    capabilities = ['graph', 'help']

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
        log.debug('Graph extraction plugin running with arguments %s' % args)

        opts = self.options()

        adapter = ZenAdapter()
        try:
            (options, arguments) = opts.parse_args(args)
            log.debug('Done parsing arguments.  Options are "%s", arguments expanded to %s' % (options, arguments))
        except OptionError, message:
            return str(message)
        if options.deviceName is None or (not options.list and options.graphName is None):
            return 'NO.  You must specify both device and graph with -d and -g.'

        devices = adapter.devices(options.deviceName)
        if len(devices) == 0:
            return 'Cannot find a device, ip or mac for "%s"' % options.deviceName
        log.debug('Found %d devices matching %s' % (len(devices), devices))
        if options.list:
            message=''
            if options.subComponent:
                for device in devices:
                    componentList = adapter.components(device, options.subComponent)
                    if componentList:
                        for component in componentList:
                            for validGraph in component.getDefaultGraphDefs():
                                message += validGraph['title']  + ' (' + component.absolute_url_path().split(device.id)[1][1:] + ')\n'
            else:
                for device in devices:
                    for validGraph in device.getDefaultGraphDefs():
                        message += validGraph['title']  + '\n'
            return 'Valid graphs:\n' + message
        log.debug('Going to look for graph %s' % options.graphName)
        # rrdtool cannot accept arguments in unicode, so convert graphName to ascii first
        message = self.obtainValues(adapter, devices, options.graphName.encode('ascii', 'ignore'), options.subComponent, log)
        return message

    def obtainValues(self, adapter, devices, graph, component, log):
        import time
        message = ''
        log.debug('Have %d devices to check for %s' % (len(devices), graph))
        for device in devices:
            log.debug('Checking %s. For the graph %s' % (device.id, graph))
            # try to get it directly from the device first.
            if self.hasGraph(device, graph):
                log.debug('The device %s does have the graph %s' % (device.id, graph))
                message += '%s %s: %s\n' % (device.name(), graph, self.shorten(self.upload(self.render(device.getGraphDefUrl(graph)), device.name() + '/' +  graph.replace(' ', '_') + '_' + time.strftime('%Y%m%d_%H%M%S',time.localtime()) +'.png')))
            elif component is not None:
                compList = adapter.components(device, component)
                if not compList:
                    return 'Sorry.  Cannot find a component %s on %s' % (component, device)
                if len(compList)>1:
                    return 'Multiple components found. Please, define more exaclty.'
                comp=compList[0]
                log.debug('Looking for graph %s in component %s' % (graph, comp.name()))
                if self.hasGraph(comp, graph):
                    message += '%s %s %s: %s\n' % (device.name(), component, graph, self.shorten(self.upload(self.render(comp.getGraphDefUrl(graph)), device.name() +  comp.absolute_url_path()[comp.absolute_url_path().find(device.id)+len(device.id):] + '/' + graph.replace(' ', '_') +'_' + time.strftime('%Y%m%d_%H%M%S',time.localtime()) +'.png')))
                else:
                    message += '%s %s: Does not have a graph named %s.  Remember, spelling and case matter.  Try -l for a list of graphs' % (device.name(), component, graph)
            else:
                message += '%s: Unable to find the graph %s. Remember, spelling and case matter.  Try -l for a list of graphs' % (device.name(), graph)
        return message

    def hasGraph(self, entity, graph):
        hasGr = False
        for gr in entity.getDefaultGraphDefs():
            if gr['title'] == graph:
                hasGr = True
                break
        return hasGr

    def render(self, url):
        from urlparse import urlparse, parse_qsl
        import StringIO
        png = StringIO.StringIO()
        from Products.ZenRRD.zenrender import RenderServer
        png.write(eval('RenderServer("").render('+','.join(['%s="%s"' % k for k in parse_qsl(urlparse(url)[4])])+')'))
        png.seek(0)
        return png

    def upload(self, strObj, saveAs):
        import ftplib
        con = ftplib.FTP('ftp.nm.ru', 'zenbot', 'qwe123#')
        #create path if it doesn't exists and cwd to it
        for dir in saveAs.split('/')[:-1]:
            try:
                con.cwd(dir)
            except ftplib.error_perm:
                con.mkd(dir)
                con.cwd(dir)
        con.storbinary('STOR ' + saveAs.split('/')[-1], strObj)
        con.quit()
        return 'http://zenbot.nm.ru/' + saveAs

    def shorten(self,url):
        import urllib2
        html=urllib2.urlopen("http://tinyurl.com/create.php?url=%s" % url).read()
        return html[html.find("<b>http://tinyurl.com/")+3:html.find("</b>",html.find("<b>http://tinyurl.com/"))]

    def private(self):
        return False

        # parse the options
    def options(self):
        parser = Options(description = 'Retrieve graph.  Simple example:\n graph -d 10.1.1.1 -g IO', prog = 'graph')
        parser.add_option('-d', '--device', dest='deviceName', help='Device name, IP or MAC.')
        parser.add_option('-g', '--graph', dest='graphName', help='Name of graph.')
        parser.add_option('-l', '--list', dest='list', action='store_true', help='Only list graphs for the device and/or component.')
        parser.add_option('-s', '--subcomponent', dest='subComponent', help='Optional subcomponent name, if the graph does not reside directly on the device.  You will probably have to specify this.')
        return parser

    def help(self):
        opts = self.options()
        return str(opts.help())
