""" Main module for the ConfigObj version of the EPAR task editor
$Id$
"""
from __future__ import division # confidence high

import configobj, glob, os, tkMessageBox
import cfgpars, editpar, filedlg, vtor_checks
from cfgpars import APP_NAME


# tool help
tealHelpString = """\
The TEAL (Task Editor And Launcher) GUI is used to edit task parameters in a
parameter-dependent way.  After editing, it allows the user to launch
(execute) the task.  It also allows the user to view task help in a separate
window that remains accessible while the parameters are being edited.


Editing Parameters
--------------------

Parameter values are modified using various GUI widgets that depend on the
parameter properties.  It is possible to edit parameters using either the mouse
or the keyboard.  Most parameters have a context-dependent menu accessible via
right-clicking that enables resetting the parameter (restoring its value to
the task default), clearing the value, or even activating a file browser that
allows a filename to be selected and entered into the parameter field.  Some
items on the right-click pop-up menu may be disabled depending on the parameter
type (e.g. the file browser cannot be used for numeric parameters.)

The mouse-editing behavior should be intuitive, so the notes below focus on
keyboard-editing.  When the editor starts, the first parameter is selected.  To
select another parameter, use the Tab key (Shift-Tab to go backwards) or Return
to move the focus from item to item. The Up and Down arrow keys also move
between fields.  The toolbar buttons can also be selected with Tab.  Use the
space bar to "push" buttons or activate menus.

Enumerated Parameters
        Parameters that have a list of choices use a drop-down menu.  The space
        bar causes the menu to appear; once it is present, the up/down arrow
        keys can be used to select different items.  Items in the list have
        accelerators (underlined, generally the first letter) that can be typed
        to jump directly to that item.  When editing is complete, hit Return or
        Tab to accept the changes, or type Escape to close the menu without
        changing the current parameter value.

Boolean Parameters
        Boolean parameters appear as Yes/No radio buttons.  Hitting the space
        bar toggles the setting, while 'y' and 'n' can be typed to select the
        desired value.

Text Entry Fields
        Strings, integers, floats, etc. appear as text-entry fields.  Values
        are verified to to be legal before being stored in the parameter. If an
        an attempt is made to set a parameter to an illegal value, the program
        beeps and a warning message appears in the status bar at the bottom of
        the window.

        To see the value of a string that is longer than the entry widget,
        either use the left mouse button to do a slow "scroll" through the
        entry or use the middle mouse button to "pull" the value in the entry
        back and forth quickly.  In either case, just click in the entry widget
        with the mouse and then drag to the left or right.  If there is a
        selection highlighted, the middle mouse button may paste it in when
        clicked.  It may be necessary to click once with the left mouse
        button to undo the selection before using the middle button.

        You can also use the left and right arrow keys to scroll through the
        selection.  Control-A jumps to the beginning of the entry, and
        Control-E jumps to the end of the entry.


The Menu Bar
--------------

File menu:
    Execute
             Start the task running with the currently edited parameter values.
             If the Option "Save and Close on Execute" is set, this will save
             all the parameters and close the editor window.
    Save
             Save the parameters to the file named in the title bar.  This
             does not close the editor window, nor does it execute the task.
    Save As...
             Save the parameters to a user-specified file.  This does not
             close the editor window, nor does it execute the task.
    Defaults
             Reset all parameters to the system default values for this
             task.  Note that individual parameters can be reset using the
             menu shown by right-clicking on the parameter entry.
    Close
             Close the parameter editor.  If there are unsaved changes, the
             user is prompted to save them.  Either way, this action returns
             to the calling routine a Python dict of the currently selected
             parameter values.
    Cancel
             Cancel the editing session by exiting the parameter editor.  All
             recent changes that were made to the parameters are lost (going
             back until the last Save or Save As).  This action returns
             a Python None to the calling routine.

Open... menu:
     Load and edit parameters from any applicable file found for the current
     task.  This changes the current file being edited (see the name listed
     in the title bar) to the one selected to be opened.  If no such files
     are found, this menu is not shown.

Options menu:
    Display Task Help in a Window
             Help on the task is available through the Help menu.  If this
             option is selected, the help text is displayed in a pop-up window.
             This is the default behavior.
    Display Task Help in a Browser
             If this option is selected, instead of a pop-up window, help is
             displayed in the user's web browser.  This requires access to
             the internet and is a somewhat experimental feature.  Any HTML
             version of the task's help need to be provided by the task.
    Save and Close on Execute
             If this option is selected, the parameter editing window will be
             closed right before task execution as if the Close button had
             been clicked.  This is the default behavior.  For short-running
             tasks, it may be interesting to leave TEAL open and continue to
             execute while tweaking certain parameter values.

Help menu:
    Task Help
             Display help on the task whose parameters are being edited.
             By default the help pops up in a new window, but the help can also
             be displayed in a web browser by modifying the Options.
    EPAR Help
             Display this help.


Toolbar Buttons
-----------------

The Toolbar contains a set of buttons that provide shortcuts for the most
common menu bar actions.  Their names are the same as the menu items given
above: Execute, Save, Close, Cancel, and Defaults.

Note that the toolbar buttons are accessible from the keyboard using the Tab
and Shift-Tab keys.  They are located in sequence before the first parameter.
If the first parameter is selected, Shift-Tab backs up to the "Task Help"
button, and if the last parameter is selected then Tab wraps around and selects
the "Execute" button.
"""


# Starts a GUI session
def teal(theTask, parent=None, isChild=0, loadOnly=False):
    if loadOnly:
        return cfgpars.getObjectFromTaskArg(theTask)
    else:
        dlg = ConfigObjEparDialog(theTask, parent, isChild)
        if dlg.canceled():
            return None
        else:
            return dlg.getTaskParsObj()


# .cfgspc embedded code execution is done here, in a relatively confined space
def execTriggerCode(SCOPE, NAME, VAL, codeStr):
    # The variables available to the code to be executed are:
    #     SCOPE, NAME, VAL
    # The code string itself is expected to set a var named OUT
    OUT = None
    exec codeStr
    return OUT


# Main class
class ConfigObjEparDialog(editpar.EditParDialog):

    def __init__(self, theTask, parent=None, isChild=0,
                 title=APP_NAME, childList=None):

        # Init base - calls _setTaskParsObj(), sets self.taskName, etc
        editpar.EditParDialog.__init__(self, theTask, parent, isChild,
                                       title, childList,
                                       resourceDir=cfgpars.getAppDir())
        # We don't return from this until the GUI is closed


    def _overrideMasterSettings(self):
        """ Override so that we can run in a different mode. """
        # config-obj dict of defaults
        cod = self._getGuiSettings()

        # our own GUI setup
        self._appName             = APP_NAME
        self._appHelpString       = tealHelpString
        self._useSimpleAutoClose  = False # is a fundamental issue here
        self._showExtraHelpButton = False
        self._saveAndCloseOnExec  = cod.get('saveAndCloseOnExec', True)
        self._showHelpInBrowser   = cod.get('showHelpInBrowser', False)
        self._optFile             = APP_NAME.lower()+".optionDB"

        # our own colors
        # prmdrss teal: #00ffaa, pure cyan (teal) #00ffff (darker) #008080
        # "#aaaaee" is a darker but good blue, but "#bbbbff" pops
        ltblu = "#ccccff" # light blue
        drktl = "#008888" # darkish teal
        self._frmeColor = cod.get('frameColor', drktl)
        self._taskColor = cod.get('taskBoxColor', ltblu)
        self._bboxColor = cod.get('buttonBoxColor', ltblu)
        self._entsColor = cod.get('entriesColor', ltblu)


    def _preMainLoop(self):
        """ Override so that we can do some things right before activating. """
        # Put the fname in the title. EditParDialog doesn't do this by default
        self.updateTitle(self._taskParsObj.filename)


    def _doActualSave(self, fname, comment, set_ro=False):
        """ Override this so we can handle case of file not writable, as
            well as to make our _lastSavedState copy. """
        try:
            rv=self._taskParsObj.saveParList(filename=fname,comment=comment)
        except IOError:
            # User does not have privs to write to this file. Get name of local
            # choice and try to use that.
            if not fname:
                fname = self._taskParsObj.filename
            fname = self._rcDir+os.sep+os.path.basename(fname)
            # Tell them the context is changing, and where we are saving
            msg = 'Installed config file for task "'+ \
                  self._taskParsObj.getName()+'" is not to be overwritten.'+ \
                  '  Values will be saved to: \n\n\t"'+fname+'".'
            tkMessageBox.showwarning(message=msg, title="Will not overwrite!")
            # Try saving to their local copy
            rv=self._taskParsObj.saveParList(filename=fname, comment=comment)
            # Treat like a save-as
            self._saveAsPostSave_Hook(fname)

        # Limit write privs if requested (only if not in _rcDir)
        if set_ro and os.path.dirname(os.path.abspath(fname)) != \
                                      os.path.abspath(self._rcDir):
            cfgpars.checkSetReadOnly(fname)

        # Before returning, make a copy so we know what was last saved.
        # The dict() method returns a deep-copy dict of the keyvals.
        self._lastSavedState = self._taskParsObj.dict()
        return rv


    def _saveAsPostSave_Hook(self, fnameToBeUsed_UNUSED):
        """ Override this so we can update the title bar. """
        self.updateTitle(self._taskParsObj.filename) # _taskParsObj is correct


    def hasUnsavedChanges(self):
        """ Determine if there are any edits in the GUI that have not yet been
        saved (e.g. to a file). """

        # Sanity check - this case shouldn't occur
        assert self._lastSavedState != None, \
               "BUG: Please report this as it should never occur."

        # Force the current GUI values into our model in memory, but don't
        # change anything.  Don't save to file, don't even convert bad
        # values to their previous state in the gui.  Note that this can
        # leave the GUI in a half-saved state, but since we are about to exit
        # this is OK.  We only want prompting to occur if they decide to save.
        badList = self.checkSetSaveEntries(doSave=False, fleeOnBadVals=True,
                                           allowGuiChanges=False)
        if badList:
            return True

        # Then compare our data to the last known saved state.  MAKE SURE
        # the LHS is the actual dict (and not 'self') to invoke the dict
        # comparison only.
        return self._lastSavedState != self._taskParsObj


    # Employ an edited callback for a given item?
    def _defineEditedCallbackObjectFor(self, parScope, parName):
        """ Override to allow us to use an edited callback. """

        # We know that the _taskParsObj is a ConfigObjPars
        triggerStr = self._taskParsObj.getTriggerStr(parScope, parName)

        # Some items will have a trigger, but likely most won't
        if triggerStr:
            return self
        else:
            return None


    def edited(self, scope, name, lastSavedVal, newVal):
        """ This is the callback function invoked when an item is edited.
            This is only called for those items which were previously
            specified to use this mechanism.  We do not turn this on for
            all items because the performance might be prohibitive. """

        triggerName = self._taskParsObj.getTriggerStr(scope, name)

        # First handle the known/canned trigger names
        if triggerName == '_section_switch_':
            state = str(newVal).lower() in ('on','yes','true')
            self._toggleSectionActiveState(scope, state, (name,))
            return

        # Now handle rules with embedded code (e.g. triggerName == '_rule1_')
        if '_RULES_' in self._taskParsObj and \
           triggerName in self._taskParsObj['_RULES_'].configspec:
            ruleSig = self._taskParsObj['_RULES_'].configspec[triggerName]
            chkArgsDict = vtor_checks.sigStrToKwArgsDict(ruleSig)
            codeStr = chkArgsDict.get('code')
            # SECURITY NOTE: because this part executes arbitrary code, that
            # code string must always be found only in the configspec file,
            # which is intended to only ever be root-installed w/ the package.
            if codeStr:
                # execute it and retrieve the outcome
                outval = execTriggerCode(scope, name, newVal, codeStr)
                # Leave this debug line in until it annoys someone
                print name+': '+triggerName+" --> "+str(outval)
                # Now that we have triggerName evaluated to outval, we need to
                # look through all of the parameters and see if there are any
                # items to be affected by triggerName (e.g. '_rule1_')
                self._applyTriggerValue(triggerName, outval)
                return

        # Unknown/unusable trigger
        raise RuntimeError('Unknown trigger for: "'+name+'", named: "'+ \
                           triggerName+'".  Please consult the .cfgspc file.')


    def _setTaskParsObj(self, theTask):
        """ Overridden version for ConfigObj. theTask can be either
            a .cfg file name or a ConfigObjPars object. """
        # Create the ConfigObjPars obj
        self._taskParsObj = cfgpars.getObjectFromTaskArg(theTask)
        # Immediately make a copy of it's un-tampered internal dict.
        # The dict() method returns a deep-copy dict of the keyvals.
        self._lastSavedState = self._taskParsObj.dict()


    def _getSaveAsFilter(self):
        """ Return a string to be used as the filter arg to the save file
            dialog during Save-As. """
        filt = os.path.dirname(self._taskParsObj.filename)+'/*.cfg'
        envVarName = APP_NAME.upper()+'_CFG'
        if envVarName in os.environ:
            upx = os.environ[envVarName]
            if len(upx) > 0:  filt = upx+"/*.cfg" 
        return filt


    def _getOpenChoices(self):
        """ Go through all possible sites to find applicable .cfg files.
            Return as an iterable. """
        tsk = self._taskParsObj.getName()
        taskFiles = set()
        dirsSoFar = [] # this helps speed this up (skip unneeded globs)

        # last dir
        aDir = os.path.dirname(self._taskParsObj.filename)
        if len(aDir) < 1: aDir = os.curdir
        dirsSoFar.append(aDir)
        taskFiles.update(cfgpars.getCfgFilesInDirForTask(aDir, tsk))

        # current dir
        aDir = os.getcwd()
        if aDir not in dirsSoFar:
            dirsSoFar.append(aDir)
            taskFiles.update(cfgpars.getCfgFilesInDirForTask(aDir, tsk))

        # task's python pkg dir (if tsk == python pkg name)
        try:
            x, pkgf = cfgpars.findCfgFileForPkg(tsk, '.cfg', taskName=tsk,
                              pkgObj=self._taskParsObj.getAssocPkg())
            taskFiles.update( (pkgf,) )
        except cfgpars.NoCfgFileError:
            pass # no big deal - maybe there is no python package

        # user's own resourceDir
        aDir = self._rcDir
        if aDir not in dirsSoFar:
            dirsSoFar.append(aDir)
            taskFiles.update(cfgpars.getCfgFilesInDirForTask(aDir, tsk))

        # extra loc - see if they used the app's env. var
        aDir = dirsSoFar[0] # flag to skip this if no env var found
        envVarName = APP_NAME.upper()+'_CFG'
        if envVarName in os.environ: aDir = os.environ[envVarName]
        if aDir not in dirsSoFar:
            dirsSoFar.append(aDir)
            taskFiles.update(cfgpars.getCfgFilesInDirForTask(aDir, tsk))

        # At the very end, add an option which we will later interpret to mean
        # to open the file dialog.
        taskFiles = list(taskFiles) # so as to keep next item at end of seq
        taskFiles.sort()
        taskFiles.append("Other ...")

        return taskFiles


    # OPEN: load parameter settings from a user-specified file
    def pfopen(self, event=None):
        """ Load the parameter settings from a user-specified file. """

        # Get the selected file name
        fname = self._openMenuChoice.get()

        # Also allow them to simply find any file - do not check _task_name_...
        # (could use Tkinter's FileDialog, but this one is prettier)
        if fname[-3:] == '...':
            fd = filedlg.PersistLoadFileDialog(self.top, "Load Config File",
                                               self._getSaveAsFilter())
            if fd.Show() != 1:
                fd.DialogCleanup()
                return
            fname = fd.GetFileName()
            fd.DialogCleanup()
            if fname == None: return # canceled

        # load it into a tmp object (use associatedPkg if we have one)
        tmpObj = cfgpars.ConfigObjPars(fname, associatedPkg=\
                                       self._taskParsObj.getAssocPkg())

        # check it to make sure it is a match
        if not self._taskParsObj.isSameTaskAs(tmpObj):
            msg = 'The current task is "'+self._taskParsObj.getName()+ \
                  '", but the selected file is for task "'+tmpObj.getName()+ \
                  '".  This file was not loaded.'
            tkMessageBox.showerror(message=msg,
                title="Error in "+os.path.basename(fname))
            return

        # Set the GUI entries to these values (let the user Save after)
        newParList = tmpObj.getParList()
        try:
            self.setAllEntriesFromParList(newParList, updateModel=True)
                # go ahead and updateModel, even though it will take longer,
                # we need it updated for the copy of the dict we make below
        except editpar.UnfoundParamError, pe:
            tkMessageBox.showwarning(message=pe.message, title="Error in "+\
                                     os.path.basename(fname))

        # This new fname is our current context
        self.updateTitle(fname)
        self._taskParsObj.filename = fname # !! maybe try setCurrentContext() ?
        self.freshenFocus()

        # Since we are in a new context (and have made no changes yet), make
        # a copy so we know what the last state was.
        # The dict() method returns a deep-copy dict of the keyvals.
        self._lastSavedState = self._taskParsObj.dict()


    def unlearn(self, event=None):
        """ Override this so that we can set to default values our way. """
        self._setToDefaults()
        self.freshenFocus()


    def _setToDefaults(self):
        """ Load the default parameter settings into the GUI. """

        # Create an empty object, where every item is set to it's default value
        try:
            tmpObj = cfgpars.ConfigObjPars(self._taskParsObj.filename,
                                           associatedPkg=\
                                           self._taskParsObj.getAssocPkg(),
                                           setAllToDefaults=True)
            self.showStatus("Loading default "+self.taskName+" values via: "+ \
                 os.path.basename(tmpObj._original_configspec), keep=2)
        except Exception, ex:
            msg = "Error Determining Defaults"
            tkMessageBox.showerror(message=msg+'\n\n'+ex.message,
                                   title="Error Determining Defaults")
            return

        # Set the GUI entries to these values (let the user Save after)
        newParList = tmpObj.getParList()
        try:
            self.setAllEntriesFromParList(newParList) # needn't updateModel yet
        except editpar.UnfoundParamError, pe:
            tkMessageBox.showerror(message=pe.message,
                                   title="Error Setting to Default Values")

    def _getGuiSettings(self):
        """ Return a dict (ConfigObj) of all user settings found in rcFile. """
        # Put the settings into a ConfigObj dict (don't use a config-spec)
        rcFile = self._rcDir+os.sep+APP_NAME.lower()+'.cfg'
        if os.path.exists(rcFile):
            return configobj.ConfigObj(rcFile, unrepr=True)
            # unrepr: for simple types, eliminates need for .cfgspc
        else:
            return {}


    def _saveGuiSettings(self):
        """ The base class doesn't implement this, so we will - save settings
        (only GUI stuff, not task related) to a file. """
        # Put the settings into a ConfigObj dict (don't use a config-spec)
        rcFile = self._rcDir+os.sep+APP_NAME.lower()+'.cfg'
        #
        if os.path.exists(rcFile): os.remove(rcFile)
        co = configobj.ConfigObj(rcFile)

        co['showHelpInBrowser']  = self._showHelpInBrowser
        co['saveAndCloseOnExec'] = self._saveAndCloseOnExec
        co['frameColor']         = self._frmeColor
        co['taskBoxColor']       = self._taskColor
        co['buttonBoxColor']     = self._bboxColor
        co['entriesColor']       = self._entsColor

        co.initial_comment = ['Automatically generated by '+\
            APP_NAME+'.  All edits will eventually be overwritten.']
        co.initial_comment.append('To use platform default colors, set each color to: None')
        co.final_comment = [''] # ensure \n at EOF
        co.unrepr = True # for simple types, eliminates need for .cfgspc
        co.write()


    def _applyTriggerValue(self, triggerName, outval):
        """ Here we look through the entire .cfgspc to see if any parameters
        are affected by this trigger. For those that are, we apply the action
        to the GUI widget.  The action is specified by depType. """
        # First find which items are dependent upon this trigger (cached)
        # e.g. { scope1.name1 : dep'cy-type, scope2.name2 : dep'cy-type, ... }
        depParsDict = self._taskParsObj.getParsWhoDependOn(triggerName)
        if not depParsDict: return
        if 0: print "Dependent parameters:\n"+str(depParsDict)

        # Then go through them and apply them to the items found
        for absName in depParsDict:
            used = False
            # For each dep, check through the widgets for that scope.name set
            for i in range(self.numParams):
                scopedName = self.paramList[i].scope+'.'+self.paramList[i].name
                if absName == scopedName: # a match was found
                    depType = depParsDict[absName]
                    if depType == 'active_if':
                        self.entryNo[i].setActiveState(outval)
                    elif depType == 'inactive_if':
                        self.entryNo[i].setActiveState(not outval)
                    else:
                         raise RuntimeError('Unknown dependency: "'+depType+ \
                                            '" for par: "'+scopedName+'"')
                    used = True
                    break

            # Or maybe it is a whole section
            if absName.endswith('._section_'):
                scope = absName[:-10]
                depType = depParsDict[absName]
                if depType == 'active_if':
                    self._toggleSectionActiveState(scope, outval, () )
                elif depType == 'inactive_if':
                    self._toggleSectionActiveState(scope, not outval, () )
                used = True

            # Help top debug the .cfgspc rules
            if not used:
                raise RuntimeError('UNUSED "'+triggerName+'" dependency: '+ \
                      str({absName:depParsDict[absName]}))