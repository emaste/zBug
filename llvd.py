#!/usr/bin/python
# export PYTHONPATH=/Developer/Library/PrivateFrameworks/LLDB.framework/Resources/Python

import lldb, sys, os
from PySide import QtCore, QtGui

if len(sys.argv) <= 1:
  print "Usage: llvd <executable> [<arg> ...]"
  sys.exit(1)
executable = sys.argv[1]
arguments = sys.argv[2:]

app = QtGui.QApplication(sys.argv)

font = QtGui.QFont()
font.setPointSize(12)
font.setFamily("Courier")

boldFont = QtGui.QFont(font)
boldFont.setBold(True)

class StackViewItem(QtGui.QTreeWidgetItem):
  def __init__(self):
    QtGui.QTreeWidgetItem.__init__(self)
    self.setFont(0, font)
    self.setFont(1, font)
    self.setTextAlignment(1, QtCore.Qt.AlignRight)
    self.setFont(2, font)

  def setFrame(self, frame):
    lineEntry = frame.GetLineEntry()
    line = lineEntry.GetLine()
    self.setText(0, "%d" % frame.GetFrameID())
    self.setText(1, "0x%x" % frame.GetPC())
    self.setText(2, "%s:%d" % (frame.GetFunctionName(), line))

class StackView(QtGui.QTreeWidget):
  def __init__(self, parent=None):
    QtGui.QTreeWidget.__init__(self, parent)
    self.setIndentation(0)
    self.setHeaderLabels([
      "#",
      "PC",
      "Function"
    ])

  def setThread(self, thread):
    for frame in thread:
      frameID = frame.GetFrameID()
      print "frameID=%d topLevelItemCount=%d" % (frameID, self.topLevelItemCount())
      if frameID < self.topLevelItemCount():
        stackViewItem = self.topLevelItem(frameID)
      else:
        stackViewItem = StackViewItem()
        self.addTopLevelItem(stackViewItem)
      stackViewItem.setFrame(frame)
    if self.topLevelItemCount() > 0:
      self.setCurrentItem(self.topLevelItem(0))
    self.resizeColumnToContents(0)
    self.resizeColumnToContents(1)
stackView = StackView()

stackView_dockWidget = QtGui.QDockWidget()
stackView_dockWidget.setTitleBarWidget(QtGui.QLabel("Stack"))
stackView_dockWidget.setWidget(stackView)

class LineNumberArea(QtGui.QWidget):
  def __init__(self, codeEditor):
    QtGui.QWidget.__init__(self, codeEditor)
    self.__codeEditor = codeEditor

  def sizeHint(self):
    return QtCore.QSize(self.__codeEditor.lineNumberAreaWidth(), 0)

  def paintEvent(self, event):
    self.__codeEditor.lineNumberAreaPaintEvent(event)

class CodeEditor(QtGui.QPlainTextEdit):
  def __init__(self, parent=None):
    QtGui.QPlainTextEdit.__init__(self, parent)

    self.setFont(font)

    lineNumberArea = LineNumberArea(self)
    self.__lineNumberArea = lineNumberArea

    def updateLineNumberAreaWidth(newBlockCount):
      self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
    self.blockCountChanged.connect(updateLineNumberAreaWidth)

    def updateLineNumberArea(rect, dy):
      if dy != 0:
        lineNumberArea.scroll(0, dy)
      else:
        lineNumberArea.update(0, rect.y(), lineNumberArea.width(), rect.height())

      if rect.contains(self.viewport().rect()):
        updateLineNumberAreaWidth(0)
    self.updateRequest.connect(updateLineNumberArea)

    def highlightCurrentLine():
      extraSelections = []
      if True: #not self.isReadOnly():
        selection = QtGui.QTextEdit.ExtraSelection()

        lineColor = QtGui.QColor(QtCore.Qt.yellow).lighter(160)

        selection.format.setBackground(lineColor)
        selection.format.setProperty(QtGui.QTextFormat.FullWidthSelection, True)
        selection.cursor = self.textCursor()
        selection.cursor.clearSelection()
        extraSelections.append(selection)
      self.setExtraSelections(extraSelections);
    self.cursorPositionChanged.connect(highlightCurrentLine)

    updateLineNumberAreaWidth(0)
    highlightCurrentLine()

  def resizeEvent(self, event):
    QtGui.QWidget.resizeEvent(self, event)
    cr = self.contentsRect()
    self.__lineNumberArea.setGeometry(
      QtCore.QRect(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
      )

  def lineNumberAreaWidth(self):
    digits = 1
    max = self.blockCount()
    if max < 1:
      max = 1
    while max >= 10:
      max = max / 10
      digits = digits + 1
    return 3 + self.fontMetrics().width('9') * digits + 3

  def lineNumberAreaPaintEvent(self, event):
    lineNumberArea = self.__lineNumberArea
    painter = QtGui.QPainter(lineNumberArea)
    painter.fillRect(event.rect(), QtCore.Qt.lightGray)
    block = self.firstVisibleBlock()
    blockNumber = block.blockNumber()
    top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
    bottom = top + int(self.blockBoundingRect(block).height())
    while block.isValid() and top <= event.rect().bottom():
      if block.isVisible() and bottom >= event.rect().top():
        blockNumberText = str(blockNumber + 1)
        painter.setPen(QtCore.Qt.black)
        painter.drawText(
          0, top,
          lineNumberArea.width() - 3, self.fontMetrics().height(),
          QtCore.Qt.AlignRight, blockNumberText
          )
      block = block.next()
      top = bottom
      bottom = top + int(self.blockBoundingRect(block).height())
      blockNumber = blockNumber + 1

  def moveToLine(self, lineNumber):
    document = self.document()
    block = document.findBlockByLineNumber(lineNumber-1)
    textCursor = self.textCursor()
    textCursor.setPosition(block.position())
    self.setTextCursor(textCursor)

codeDisplay = CodeEditor()
codeDisplay.setReadOnly(True)

lineEdit = QtGui.QLineEdit()

class OutputDisplay(QtGui.QTextEdit):
  def __init__(self, parent=None):
    QtGui.QTextEdit.__init__(self, parent)
    self.setFont(font)

  def appendCommand(self, text):
    self.setTextColor(QtCore.Qt.blue)
    cursor = self.textCursor()
    cursor.insertText("> " + text + "\n")

  def appendDebuggerOutput(self, text):
    self.setTextColor(QtCore.Qt.green)
    cursor = self.textCursor()
    cursor.insertText(text + "\n")

  def appendDebuggerErrorOutput(self, text):
    self.setTextColor(QtCore.Qt.red)
    cursor = self.textCursor()
    cursor.insertText(text + "\n")

  def appendProgramOutput(self, text):
    self.setTextColor(QtCore.Qt.black)
    cursor = self.textCursor()
    cursor.insertText(text + "\n")

outputDisplay = OutputDisplay()

centralLayout = QtGui.QVBoxLayout()
centralLayout.addWidget(codeDisplay)
centralLayout.addWidget(outputDisplay)
centralLayout.addWidget(lineEdit)

centralWidget = QtGui.QWidget()
centralWidget.setLayout(centralLayout)

mainWindow = QtGui.QMainWindow()
mainWindow.addDockWidget(QtCore.Qt.LeftDockWidgetArea, stackView_dockWidget)
mainWindow.setCentralWidget(centralWidget)
mainWindow.show()

files = {}

debugger = lldb.SBDebugger.Create()
debugger.SetAsync(True)

command_interpreter = debugger.GetCommandInterpreter()

print "Creating a target for '%s'" % executable
target = debugger.CreateTargetWithFileAndArch(executable, lldb.LLDB_ARCH_DEFAULT)

print "Setting a breakpoint at '%s'" % "main"
main_bp = target.BreakpointCreateByName("main", target.GetExecutable().GetFilename())

print "Lauing process with arguments " + str(arguments)
process = target.LaunchSimple (arguments, None, os.getcwd())
if not process or process.GetProcessID() == lldb.LLDB_INVALID_PROCESS_ID:
  print "Launch failed!"
  sys.exit(1)

pid = process.GetProcessID()
listener = debugger.GetListener()

def handleDebuggerEvents():
  done = False
  if not done:
    event = lldb.SBEvent()
    if listener.GetNextEvent(event):
      if event.GetBroadcaster().GetName() == "lldb.process":
        state = lldb.SBProcess.GetStateFromEvent (event)
        if state == lldb.eStateInvalid:
            # Not a state event
            print 'process event = %s' % (event)
        else:
            print "process state changed event: %s" % (lldb.SBDebugger.StateAsCString(state))
            if state == lldb.eStateStopped:
              print "process %u stopped" % (pid)
              for thread in process:
                frame = thread.GetFrameAtIndex(0)
                compileUnit = frame.GetCompileUnit()
                fileSpec = compileUnit.GetFileSpec()
                filename = fileSpec.GetFilename()
                if not filename in files:
                  f = open(filename, 'r')
                  contents = f.read()
                  f.close()
                  files[filename] = contents
                else:
                  contents = files[filename]
                codeDisplay.setDocumentTitle(filename)
                codeDisplay.setPlainText(contents)
                lineEntry = frame.GetLineEntry()
                line = lineEntry.GetLine()
                codeDisplay.moveToLine(line)
                stackView.setThread(thread)
                # index = compileUnit.FindLineEntryIndex()
                # print index
                print 'thread=%s frame=%s' % (thread, frame)
            elif state == lldb.eStateExited:
                exit_desc = process.GetExitDescription()
                if exit_desc:
                    print "process %u exited with status %u: %s" % (pid, process.GetExitStatus (), exit_desc)
                else:
                    print "process %u exited with status %u" % (pid, process.GetExitStatus ())
                # run_commands (command_interpreter, options.exit_commands)
                done = True
            elif state == lldb.eStateCrashed:
                print "process %u crashed" % (pid)
                print_threads (process, options)
                # run_commands (command_interpreter, options.crash_commands)
                done = True
            elif state == lldb.eStateDetached:
                print "process %u detached" % (pid)
                done = True
            elif state == lldb.eStateRunning:
              # process is running, don't say anything, we will always get one of these after resuming
              print "process %u resumed" % (pid)
            elif state == lldb.eStateUnloaded:
                print "process %u unloaded, this shouldn't happen" % (pid)
                done = True
            elif state == lldb.eStateConnected:
                print "process connected"
            elif state == lldb.eStateAttaching:
                print "process attaching"
            elif state == lldb.eStateLaunching:
                print "process launching"
      else:
          print 'Non-process event = %s' % (event)
  process_stdout = process.GetSTDOUT(1024)
  if process_stdout:
    outputDisplay.appendProgramOutput(process_stdout)
    while process_stdout:
      process_stdout = process.GetSTDOUT(1024)
      outputDisplay.appendProgramOutput(process_stdout)
  process_stderr = process.GetSTDERR(1024)
  if process_stderr:
    outputDisplay.appendProgramOutput(process_stderr)
    while process_stderr:
      process_stderr = process.GetSTDERR(1024)
      outputDisplay.appendProgramOutput(process_stderr)

def executeCommand():
  command = str(lineEdit.text())
  outputDisplay.appendCommand(command)
  lineEdit.clear()
  return_obj = lldb.SBCommandReturnObject()
  command_interpreter.HandleCommand(command, return_obj)
  if return_obj.Succeeded():
    outputDisplay.appendDebuggerOutput(return_obj.GetOutput())
  else:
    outputDisplay.appendDebuggerErrorOutput(return_obj.GetError())
lineEdit.returnPressed.connect(executeCommand)

timer = QtCore.QTimer()
timer.setInterval(100)
timer.timeout.connect(handleDebuggerEvents)
timer.start()

sys.exit(app.exec_())

