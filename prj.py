"""
Created on Fri Oct 22 15:59:38 2010

@author: ciccio
"""
import os
import leafinspect
from gph import graph
import log
from leaf.ptl import protocol
import copy


class project():
    def __init__(self, module, leafprot = ''):
        self._modulename = module
        
        self._metafolder = 'leaf_' + module        
        if not os.path.exists(self._metafolder):
            os.mkdir(self._metafolder)
        self.updateGraphs(leafprot)
            
            
            
    def updateGraphs(self, leafprot):
        #this is really an initGraphs
        #to be fixed
        if leafprot == '':
            leafprot = self.guessLeafProt()

        if leafprot != self._leafprot:
            self._graph.fromLeaf(leafprot)
            self._leafprot=leafprot
        
        mods = self.seekforMods()

        altgraphs = self.generateAltGraphs()
        for gname in altgraphs.keys():
            if str(gname) != '[]':
                altfolder = self._metafolder+'/'+str(gname).strip('[]').replace(', ','').replace('\'', '')
            else:
                altfolder = self._metafolder.strip('[]').replace(', ','').replace('\'', '')
            if not os.path.exists(altfolder):
                os.mkdir(altfolder)
            #NOOOOOOOOOOO: use like protocol.set_folder
            self.protocols[gname]=protocol(altgraphs[gname], mods, altfolder)
            self.protocols[gname].getGraph().toPdf(altfolder+'/graph.dot')
            #if not os.path.exists('wdir'):
            #    os.mkdir('wdir')
            #if not os.path.exists('wdir/' + gname):
            #    os.mkdir('wdir/'+gname)
            #self.protocols[gname].setWdir('wdir/'+gname)

            
    def Name(self):
        return
                            
    def getNodeGroups(self):
        nodegroups = dict()
        for node in self._graph.getNodes():
            gid = self._graph.getAttrib(node, 'group')
            if gid:
                if gid in nodegroups.keys():
                    nodegroups[gid].append(node)
                else:
                    nodegroups[gid] = [node]
        return nodegroups
        

    def combinations(self, *iterables):
     if iterables:
       for head in iterables[0]:
         for remainder in self.combinations(*iterables[1:]):
           yield [head] + remainder
     else:
       yield []
       
    def altPathToName(self, path):
        return str(path)

    def generateAltGraphs(self):
        altpaths = self.generateAltPaths()
        groups = self.getNodeGroups().values()
        for path in altpaths:
            self._altgraphs[self.altPathToName(path)] = copy.deepcopy(self._graph)
            for group in groups:
                for node in group:
                    if node not in path:
                        self._altgraphs[self.altPathToName(path)].delNode(node)
            log.send('Alternative protocol ' + self.altPathToName(path) +
                ' is: ' + str(self._altgraphs[self.altPathToName(path)]), 2)
                        
        return self._altgraphs

    def generateAltPaths(self):
        ngroups = self.getNodeGroups()
        temp = list()
        combs = self.combinations(*(ngroups.values()))
        # the following includes ugly patches because it's safer than
        # changing self.combinations, which is cryptic. Best solution
        # is still to change combinations.
        for t in combs:
            if len(t)>0:
                temp.append(t[0])
            else:
                temp.append(t)
        return temp
        
    def guessLeafProt(self):
        hislocals = self.getUserLocals()
        hisnames = hislocals.keys()
        
        if 'leafProtocol' in hisnames:
            leafprot = hislocals['leafProtocol']
            return leafprot
        else:
            raise NameError('I couldn''t find a variable called leafProtocol')


    def getUserLocals(self):
        import sys
        if self._modulename in sys.modules.keys():
            self._usermodule = sys.modules[self._modulename]
        else:
            self._usermodule = __import__(self._modulename)
        if not self._is_first_import:
            log.send('Reloading user module.', 2)
            reload(self._usermodule)
        self._is_first_import = False
        log.send('Your module is: ' + str(self._usermodule), 2)
        hislocals = dict()

        for (name, value) in leafinspect.getmembers(self._usermodule):
            hislocals[name] = value
        return hislocals
        
    def getModNames(self):
        names = self._graph.getNodes()
        log.send('Mod names are: ' + str(names), 3)
        return names
                
        
    def seekforMods(self):
        log.send('Looking for mods in user module.', 3)
        hislocals=self.getUserLocals()

        mymods=dict()
        for modname in self.getModNames():
            if modname in hislocals.keys():
                mymods[modname] = hislocals[modname]
            else:
                raise NameError('I couldn''t bind '+modname+' to any of your defined objects.')

        #resmods = dict()
        #for mod in mymods.keys():
        #    resmods[mod]=mymods[mod]
                
        return mymods
        
    def update(self):
        #self.updateGraphs(self._leafprot)
        for prot in self.protocols.values():
            prot.update(prot.getGraph(), self.seekforMods())
            
    def run(self):
        for protname in self.protocols.keys():
            log.insertBreak()
            log.send('Running instance: ' + protname)
            self.protocols[protname].run()

            
    def listAltProtocols(self):
        for protname in self.protocols:
            log.send('- ' + protname, 0)            
            log.send('  ' + str(self.protocols[protname].getGraph()))
            
    def getAltProtocol(self, protname):
        return self.protocols[protname]
        
            
    def provide(self, what):
        if len(self.protocols)==1:
            return self.protocols[self.protocols.keys()[0]].provide(what)
        else:
            resdict = dict()
            for protname in self.protocols:
                resdict[protname] = self.protocols[protname].provide(what)
            return resdict
            
    def getInputs(self, node):
        if len(self.protocols)==1:
            return self.protocols[self.protocols.keys()[0]].getInputs(node)
        else:
            resdict = dict()
            for protname in self.protocols:
                resdict[protname] = self.protocols[protname].getInputs(node)
            return resdict
            
    def newFile(self, fname):
        return fname

    protocols = dict()
    _graph = graph()
    _name = ''
    _metafolder = ''
    _leafprot = ''
    _altgraphs = dict()
    _is_first_import = True
