"""Run on Windows to build a Windows executable."""
import os
import sys
from pathlib import Path
if sys.platform != 'win32':
    raise SystemExit('Gere o executável Windows no próprio Windows.')
import PyInstaller.__main__
root=Path(__file__).resolve().parent
os.chdir(root)
PyInstaller.__main__.run(['--noconfirm','--clean','--onefile','--windowed','--name=HorizonteFinanceiro',
                         '--add-data='+str(root/'static')+os.pathsep+'static',str(root/'app.py')])
