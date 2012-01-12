"""
Created on Fri Oct 22 15:59:38 2010

@author: ciccio
"""

import os
import cPickle
import leafinspect
from leaf.log import send as dbgstr
from leaf.rrc import resource
import copy
import inspect
        
    

class protocol():
    """Leaf Protocol
    
    Manages all protocol resources and provides user interface through Python command line.
    Protocols are created by the prj class: use it to obtain a protocol object.
    """    

    def __init__(self, graph, mods, folder):
        dbgstr('Initializing protocol with root: ' + folder)
        self._metafolder = folder
        self._rootdir = os.getcwd()
        self._resmap = dict()

        self._graphres = resource('graph', os.path.join(folder,'graph.grp'))
        self._graphres.setValue(graph)
        if self._graphres.changed():
            if self._graphres.isDumped():
                self._manageGraphChange(self._graphres.getFingerprint())
        self._graphres.update()

        for res in self._getResNames():
            newres = resource(res, folder+'/'+res+'.res')
            #print res, newres
            self._addResource(res, newres)
        
        for mod in self._getNodeNames():
            newres = resource(mod, folder+'/'+mod+'.mod')
            newres.setDump(True)
            self._modules[mod] = newres

        self._updateModules(mods)

#    def show(self):
#        """Shows the Protocol Graph."""
#        dbgstr('Protocol:',0)
#        dbgstr(self._leafprot, 0)
#        dbgstr('Node attributes:', 0)
#        for node in self._getNodeNames():
#            ostr = node +': '
#            for attrib in self._nodeattribs.keys():
#                if attrib[0]==node:
#                    ostr += str(attrib[1])+'='+str(self._nodeattribs[attrib])+', '
#            dbgstr(ostr[0:-2], 0)
        
    def _update(self, graph, mods):
        dbgstr('New graph is: ' + str(graph), 3)
        dbgstr('New mods are: ' + str(mods), 3)
        self._manageGraphChange(graph)
        self._graphres.setValue(graph)
        self._graphres.update()
        self._updateModules(mods)

    def undumpall(self):
        """Deletes all dumped resources"""
        for res in self._getResNames():
            self.clearDump(res)

        if os.path.exists(self._metafolder):
            if os.listdir(self._metafolder) == []:
                os.rmdir(self._metafolder)

    def getinputs(self, mod):
        """Collects all input resources that are input to the given filter and returns a copy of them in a list."""
        innodes = self._getInNodes(mod)
        ids = [self._getGraph().getAttrib(_node, 'id') for _node in innodes]
        nodeparams = [copy.deepcopy(self._getResource(innode).getValue()) for innode in innodes]
        nodeparams=[one for (one,two) in sorted(zip(nodeparams, ids), key = lambda x:x[1])]      
        return tuple(nodeparams)

    def run(self):
        """Provides all leaf (final) resources."""
        res = dict()
        allok = True
        for leaf in self._getLeaves():
            resname = leaf
            if not self._isAvailable(resname)and not self._isDumped(resname):
                allok = False
            res[leaf]=self.provide(resname)
        if allok:
            dbgstr('Nothing to be done. Zzz...', 0)
        else:
            dbgstr('Done: all leaves available.', 0)
        return res
    
    def untrust(self, nodename):
        """Clears resource and all its dependent.""" 
        #if self._isLeaf(nodename):
        self.clear(nodename)
                
        dependents = self._getOutNodesRecursive(nodename)
        for res in self._getResNames():
            if(res in dependents):
                self.clear(res)

    def clear(self, filtername):
        """Clears and undumps a resource.""" 
        if self._isDumped(filtername):
            dbgstr('Clearing dump: ' + str(filtername), 2)
            self._getResource(filtername).clearDump()
        if self._isAvailable(filtername):
            dbgstr('Clearing resource: ' + str(filtername))
            self._resmap[filtername].clear()

    def provide(self, resname):
        """Provides a resource.
        
        The resource is returned if available, loaded from disk if dumped, produced
        on the fly otherwise.
        """
        if type(resname) != str:
            resname = resname.__name__
        return self._provideResource(resname).getValue()
            
    def dumpOn(self):
        """Switches dumping ON."""
        self._dodump = True

    def dumpOff(self):
        """Switches dumping OFF."""
        self._dodump = False
        
    def trust(self, who, what):
        """Assign a resource to a filter without invalidating dependent resources."""
        if type(who) == str:
            dbgstr('I\'m assuming that using ' + str(what) + ' for ' + who + ' won\'t have consequences on other nodes.', 0)
            self._setMod(who,what)
        elif type(who) == tuple:
            dbgstr('I\'m assuming that using your object of type ' + str(type(what)) + ' for ' + str(who) + ' won\'t have consequences on other nodes.', 0)
            self._addResource(who,what)        
        
    def list(self):
        """Lists the state of all resources."""
        mystr = ''
        for res in self._getResNames():
            mystr+=str(res)+'\t '
            if self._isAvailable(res):
                mystr+='available\t'
            else:
                mystr+='NOT available\t'
            if self._isDumped(res):
                mystr+='dumped'
            else:
                mystr+='NOT dumped'
            mystr += '\n'
        print mystr
        
    def export(self, ofile, layout='LR'):
        """Exports the protocol to a pdf file."""
        import textwrap
        ofile = self._metafolder+'/'+ofile
        f=open(ofile, 'w')
        f.write('digraph G {'+
                'node [shape=box, style=rounded];'+
                'rankdir='+
                ('TB' if layout.lower()=='TB' else 'LR')+
                ';')
        for idx, node in enumerate(self._getGraph().getNodes()):
            f.write(str(node))
            docstr = inspect.getdoc(self._modules[node].getValue()) if type(self._modules[node].getValue())==type(inspect.getdoc) else None
            f.write('[label = <<table border="0"><tr><td><B>' +
                    node +
                    '</B></td></tr><tr><td align = "left"><font POINT-SIZE="10">'+
                   ('-' if docstr == None else  textwrap.fill(docstr, 30)).replace('\n','<br/>') +
                    '</font></td></tr></table>>]\n')
        for node in self._getGraph().keys():
            for onode in self._getGraph()[node]:
                f.write(node + ' -> ' + onode + '\n')
        f.write('}')
        f.close()
        os.system('dot -Tpdf -o' + ofile + '.export ' + ofile)


    def _updateModules(self, mods):
        for modname in mods:
            if modname in self._modules.keys():
                self._modules[modname].setValue(mods[modname])
                if self._modules[modname].changed():
                    self.untrust(self._modules[modname].name())
                    self._modhelp[modname] = inspect.getdoc(self._modules[modname].getValue())
                self._modules[modname].update()
            else:
                dbgstr('New module: ' + modname)
                self._modules[modname] = resource(modname,
                    self._metafolder+'/'+modname+'.dmp' )
                self._modules[modname].setValue(mods[modname])
                self._modules[modname].update()                
                

    def _manageGraphChange(self, newGraph):
        #checking for change in graph structure
        #a node is untrusted if its inputs have changed
        oldg = self._graphres.getValue()

        for node in newGraph.getNodes():
            if node in oldg.getNodes():
                innodes1 = newGraph.getInNodes(node)
                innodes2 = oldg.getInNodes(node)
                for inNode in innodes1:
                    if not inNode in innodes2:
                        dbgstr('Inputs to ' + node + 'have changed, untrusting it.')

    
            
#    def modSummary(self):
#        pass
#        #for mod in self._getNodeNames():
#        #    dbgstr(mod + ', changed = ' + self.checkModChanged(modname,))
            
    def _getContents(self, mod):
        try:
            leafinspect.getsource(mod)
            value = leafinspect.getsource(mod)
        except Exception:            
            value = mod
        return value
        
        

        
    #def checkModChanged(self, modname, mod):                
        #return mod.checkChanged(), mod.getFingerprint()
        
#        isnew = False
#        if not self._modules.has_key(modname):
#            self._modules[modname].setValue(None)
#            isnew = True
#            haschanged = True
#            try:
#                leafinspect.getsource(mod)
#                fprint = leafinspect.getsource(mod)
#            except Exception:
#                dbgstr('No source code for \''+modname+'\': will store value.', 2)
#                fprint = mod
#                        
#        elif type(mod) == File:
#            haschanged = mod.hasChanged()
#            fprint = mod
#
#        else:
#            try:
#                haschanged = self._modules[modname].getFingerprint() != leafinspect.getsource(mod)
#                fprint = leafinspect.getsource(mod.getValue())
#            except Exception:
#                dbgstr('No source code for \''+modname+'\': will store value.', 2)
#                haschanged = self._modules[modname].get() != mod
#                fprint = mod
#            
#        if isnew: dbgstr('New module: ' + modname, 0)
#        elif haschanged:
#            dbgstr('Changed module: ' + modname, 0)
#        
#        return haschanged, fprint

    def _setMod(self, modname, mod):
        haschanged = self._modules[modname].changed()
        if haschanged:
            if type(mod) == File:
                mod.update()
            self._modules[modname].setValue(mod.getValue())
            self._modules[modname].updateFingerprint()
            self.untrust(modname)
            dependents = self._getOutNodesRecursive(modname)
            if dependents != []:
                dbgstr('These nodes are dependent: '+str(dependents), 0)
            #for dep in dependents:
            #    self._clearFilter(dep)

    def _setMods(self, mods):
        self._modules = mods
        for modname in mods.keys():
            self._setMod(modname, mods[modname])
        
        dbgstr('Modules are: ' + str(self._modules), 3)
        #dbgstr('with source: ' + str(self._modcontents), 3)

        

    def _getInputNames(self, node):
        dbgstr(str(self._graphres.getValue()._getInNodes(node)))
        
    def _dumpResource(self, res):
        self._getResource(res).dump()
        
    def _newResource(self, resname, resval):
        dbgstr('Updating resource: ' + resname, 2)
        dbgstr('with contents: ' + str(resval), 3)
        self._getResource(resname).setValue(resval)
        self._getResource(resname).updateFingerprint()
        self._dumpResource(resname)
        
    def _clearFilter(self, nodename):
        if self._isLeaf(nodename):
            self.clear(nodename)
        for node in self._getOutNodes(nodename):
            self.clear(node)

  
            
    def _setWdir(self, wdir):
        self.wdir = wdir            
        
    def _isAvailable(self, resname):
        dbgstr('Checking resource: ' + str(resname), 3)
        if self._getResource(resname).isAvailable():
           dbgstr('Available: ' + str(resname), 3)
           return True
        dbgstr('Unavailable: ' + str(resname), 3)
        return False        

                
    def _getResource(self, resname):
        dbgstr('Getting resource: ' + str(resname), 3)        
        return self._resmap[resname]
        
    def _addResource(self, name, res):
        self._resmap[name]=res
            
    def _provideResource(self, resname):
        dbgstr('Providing resource: ' + str(resname), 2)
        if self._isAvailable(resname):
            dbgstr('Found in RAM: ' + str(resname))
            dbgstr('Resource content is:\n' + str(self._getResource(resname)) ,4)
            return self._getResource(resname)
        elif self._isDumped(resname):
            dbgstr('Found on disk: ' + str(resname))
            self._addResource(resname, self._loadResource(resname))
            dbgstr('Resource content is:\n' + str(self._getResource(resname)), 4)
            return self._resmap[-1]
        else:
            dbgstr('Resource not found. I need to run first: ' + str(resname))
            self._runNode(resname)
            return self._getResource(resname)

    def _getNodeNames(self):
        return self._getGraph().getNodes()
        
    def _isResFile(self, res):
        isit = res.isFile()
        if isit : dbgstr(str(res) + ' is a file.')
        return isit

    def _runNode(self, node):
        dbgstr('Running node: ' + str(node))
        
        nodeparams = list()        
        input_nodes = self._getInNodes(node)
        for item in input_nodes:
            thisnode_inputs = list()
            neededres = item
            dbgstr('Retreiving resource: ' + neededres)
            this_params = self._provideResource(neededres)
            if type(this_params.getValue())==list:
                dbgstr('Resource type is: list.', 2)
                for this_param in this_params.getValue():
                    thisnode_inputs.append(this_param)
            elif self._isResFile(this_params):
                dbgstr('Resource type is: file.', 2)
                thisnode_inputs.append(this_params.getValue())
            else:
                dbgstr('Resource type is: ' + str(type(this_params.getValue())), 2)
                thisnode_inputs.append(this_params.getValue())
            if len(thisnode_inputs)==1:
                nodeparams.append(thisnode_inputs[0])
            else:
                nodeparams.append(thisnode_inputs)
        
        #sorting basing on ids        
        #ids = [self._getGraph().getAttrib(_node, 'id') for _node in input_nodes]
        #nodeparams=[one for (one,two) in sorted(zip(nodeparams, ids), key = lambda x:x[1])]

        #sorting basing on alphabetic order of module name
        nodeparams=[one for (one,two) in sorted(zip(nodeparams, input_nodes), key = lambda x:x[1])]
        

        dbgstr('Ready to run: ' + node, 2)
        dbgstr('through ' + str(self._getModule(node).getValue()), 2)
        dbgstr('on input:\n\t' + str(nodeparams), 3)
        
        return self._callMod(node, nodeparams)
        
    def _getModule(self, name):
        return self._modules[name]
        
    def _callMod(self, node, nodeparams):
        
        if not self._checkIsFunction(self._modules[node].getValue()):
            dbgstr('Node '+node+' is not a function: passing itself.', 2)            
            newres = self._modules[node].getValue()
            self._processRawRes(node, newres)
            
        elif len(nodeparams)==0:
            dbgstr('No input for: ' + str(node), 1)
            dbgstr('Running node: ' + node)
            newres = apply(self._modules[node].getValue(), [])
            dbgstr('Done.')
            dbgstr('Produced list:\n\t' + str(newres), 3)
            self._processRawRes(node, newres)
    
        elif self._getGraph().getAttrib(node, 'hash'):
            dbgstr('Inputs are joined.', 2)
            dbgstr('Running node: ' + node)
            newres = apply(self._modules[node].getValue(), nodeparams)
            dbgstr('Done.', 0)
            dbgstr('Produced list:\n\t' + str(newres), 3)
            self._processRawRes(node, newres)
            
        else:
            dbgstr('Inputs are hashed.', 2)
            for nodeparam in nodeparams:
                dbgstr('Running node: ' + node)
                newres = self._modules[node].getValue()(nodeparam)
                dbgstr('Done.')
                dbgstr('Produced list:\n\t' + str(newres), 3)
                self._processRawRes(node, newres)
            
        return newres
        
    def _checkIsFunction(self, x):
        #return hasattr(self._modules[node].getValue(), '_call_'):
        return type(lambda y:y)==type(x)
        
    def _placeFileRes(self, fname):
        if self._auto_place_files:
            os.system('mv -r"'+ fname + '" ' + self._metafolder)
            
    def _buildResName(self, inode, onode, rawres):
        if onode == None:
            return inode
        else:
            return inode
        

    def _isFileMod(self, node):
        flags = self._getGraph().getAttrib(node, 'LEAF_FLAGS')
        if flags == None:
            return False
        return 'f' in flags or 'F' in flags
        
    def _updateFilePath(self, path):
        parts = os.path.split(path)
        if parts[0] != self._metafolder:
            return self._metafolder + '/' + parts[1]
        return path

    def _processRawRes(self, node, rawres):
        

                        
# #        elif type(rawres)==tuple:        
# #            dbgstr('Raw list are packed in a tuple.')
# #            
# #            if len(rawres != len(self._getGraph()[node])):
# #                raise NameError('When a module returns a tuple, it''s length must be equal to the number of the module''s outputs.')
# #                
# #            for idx, outnode in enumerate(self._getGraph()[node]):
# #                newresname = self._buildResName(node, outnode, rawres)                
# #                dbgstr('Requesting add resource: ' + str(newresname))
# #                if self._isFileMod(node):
# #                    self._placeFileRes(rawres)
# #                    self._newResource(newresname, self._updateFilePath(rawres[idx]))
# #                else:
# #                    self._newResource(newresname, rawres[idx])
# #                
# #        else:

        # if self._isFileMod(node):
        #     if type(rawres)==tuple or type(rawres)==list:
        #         for rawresi in rawres:
        #             newresname = self._buildResName(node, None, rawresi)
        #             dbgstr('Requesting add resource: ' + node, 2)
        #             self._placeFileRes(rawresi)
        #             self._newResource(newresname, self._updateFilePath(rawresi))
        #     else:
        #         newresname = self._buildResName(node, None, rawres)
        #         dbgstr('Requesting add resource: ' + node, 2)
        #         self._placeFileRes(rawres)
        #         self._newResource(newresname, self._updateFilePath(rawres))
        # else:
        #     newresname = self._buildResName(node, None, rawres)
        #     dbgstr('Requesting add resource: ' + node, 2)
        #     self._newResource(newresname, rawres)
        newresname = self._buildResName(node, None, rawres)
        dbgstr('Requesting add resource: ' + node, 2)
        self._newResource(newresname, rawres)
                
                
                
    def _setDumpFolder(self,f):
        self._metafolder=f

 
            
    def _isDumped(self, resname):
        return self._getResource(resname).isDumped()

    def _loadResource(self, res):
        dbgstr('Getting resource ' + str(res) + ' from disk.', 2)
        if self._isDumped(res):
            dbgstr('Resource ' + str(res) + ' found in: ' + res.getDumpPath() ,2)
            return cPickle.load(open(res.getDumpPath(), 'r'))
        else:
            dbgstr('Resource ' + str(res) + ' not found on disk! I\'ve been looking for: ' + res.getDumpPath())

    def _ChangeME_resToPath(self, res):
        if self._getGraph().getAttrib(res[0], 'hashout'):
            if res[0] == None: first_part = ''
            else: first_part = res[0]
            if res[1] == None: second_part = ''
            else: second_part = res[1]
            if first_part != '' and second_part !='':
                mid_part = 'TO'
            else: mid_part = ''
        
            fname = first_part + mid_part + second_part + '.dmp'
        else:
            fname = res[0]
            
        dbgstr('Dump file for resource ' + str(res) + ' is ' + self._metafolder + '/' + fname, 2)
        return self._metafolder + '/' + fname


    def _getInNodes(self, node):
        g = self._reverseGraph(self._getGraph())
        dbgstr('in-nodes of ' + str(node) + ' are: ' + str(g[node]), 2)
        return g[node]
        
    def _getOutNodes(self, node):
        #dbgstr('out-nodes of ' + str(node) + ' are: ' + str(self._graph[node]), 2)
        return self._getGraph()[node]
        
    def _isLeaf(self, node):
        return self._getGraph()[node]==[]
        
    def _getOutNodesRecursive(self, node):
        alloutnodes = list()
        nodestack = list(self._getOutNodes(node))
        while nodestack!=[]:
            onode = nodestack.pop()
            nodestack.extend(self._getOutNodes(onode))
            alloutnodes.append(onode)
        return alloutnodes

    def _getLeaves(self):
        leaves = list()
        for key in self._getGraph().keys():
            if self._getGraph()[key]==[]:
                leaves.append(key)
        return leaves

        
    def _getResNames(self):
        return self._getGraph().getNodes()
#        resnames = list()
#        for node in self._getGraph().keys():
#            if self._getOutNodes(node) == []:
#                resname = (node, None)
#                if not resname in resnames:
#                    resnames.append(resname)
#            else:
#                for onode in self._getOutNodes(node):
#                    resname = (node, onode)
#                    if not resname in resnames:
#                        resnames.append(resname)
#        dbgstr('Resource names: ' + str(resnames), 3)
#        return resnames


    def _reverseGraph(self, g):
        all_values = list()
        for item in g.values():
            for subitem in item:
                if not (subitem in all_values):
                    all_values.append(subitem)
        
        rg=dict.fromkeys(all_values)
        for key in rg:
            rg[key] = []
        for value in all_values:
            for key in g.keys():
                if value in g[key]:
                    rg[value].append(key)
        for value in g.keys():
            if not(value in rg.keys()):
                rg[value]=[]
        return rg
        
        
    def _setDumping(self, d):
        self._dodump = d
        
                
    def _getGraph(self):
        return self._graphres.getValue()
        
        
#    def updateFiles(self):
#        for res in self._modmap:
#            if res.isFile():
#                if res.Value().hasChanged():
#                    dbgstr('File resource '+str(res)+ ' has changed.')
                                    
    def _setMod(self, who, what):
        self._modcontents[who.getName()] = self._getContents(what)
        self.dumpMods()
        
#    def _setRes(self, who, what):
#        self._resmap[self._resmap.index(who)]=what
#        self._dumpResource(who)
                        
            
    def _loadMods(self):
        if os.path.exists(self.modsToPath()):
            mods = cPickle.load(open(self.modsToPath(), 'r'))
        else:
            mods = dict()
        
        dbgstr('Found on disk: ' + str(mods.keys()), 2)
        return mods


        
    def _setMetaFolder(self, f):
        self._metafolder = f


    def _getresmap(self):
        return self._resmap
        
                    
    _resmap = dict()
    _graphres = None
    _metafolder = 'leafmeta'
    _dodump = True
    _modules = dict()
    _modhelp = dict()
    _auto_place_files = False
