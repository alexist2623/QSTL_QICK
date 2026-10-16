from pathlib import Path
import sys, json, os, time, socket, gc
ROOT=Path(__file__).resolve().parent
CONFIG=json.loads((ROOT/'selection.json').read_text(encoding='utf-8'))
selected=list(dict.fromkeys(n for nodes in CONFIG['categories'].values() for n in nodes))
class OfflineSocket(socket.socket):
    def connect(self,*args,**kwargs): raise RuntimeError('Network disabled during focused software validation')
    def connect_ex(self,*args,**kwargs): raise RuntimeError('Network disabled during focused software validation')
socket.socket=OfflineSocket
import qick.sim
from PyQt5 import QtCore, QtWidgets
APP=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
import pytest
class Evidence:
    def __init__(self): self.collected=[]; self.reports=[]
    def pytest_collection_finish(self,session):
        self.collected=[item.nodeid for item in session.items]
        (ROOT/'collected.json').write_text(json.dumps(self.collected,indent=2),encoding='utf-8')
        if len(self.collected)!=len(set(self.collected)): raise RuntimeError('Duplicate collected test IDs')
    def pytest_runtest_logreport(self,report):
        self.reports.append({'nodeid':report.nodeid,'when':report.when,'outcome':report.outcome,'duration':report.duration,'longrepr':str(report.longrepr) if report.failed else None})
        with (ROOT/'events.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(self.reports[-1])+'\n')
    def pytest_sessionfinish(self,session,exitstatus):
        records=[]
        for nodeid in self.collected:
            phases=[r for r in self.reports if r['nodeid']==nodeid]
            outcome='failed' if any(r['outcome']=='failed' for r in phases) else 'skipped' if any(r['outcome']=='skipped' for r in phases) else 'passed' if any(r['when']=='call' and r['outcome']=='passed' for r in phases) else 'not_run'
            cats=[cat for cat,nodes in CONFIG['categories'].items() if any(nodeid==n or nodeid.startswith(n+'[') for n in nodes)]
            records.append({'nodeid':nodeid,'outcome':outcome,'categories':cats,'phases':phases})
        payload={'pytest_exitstatus':int(exitstatus),'unique_collected':len(set(self.collected)),'counts':{state:sum(r['outcome']==state for r in records) for state in ('passed','failed','skipped','not_run')},'tests':records}
        (ROOT/'pytest_results.json').write_text(json.dumps(payload,indent=2),encoding='utf-8')
plugin=Evidence()
result=pytest.main(['-q','-p','no:cacheprovider','--basetemp='+str(ROOT/'pytest_tmp'),'--junitxml='+str(ROOT/'junit.xml'),*selected],plugins=[plugin])
APP.processEvents()
for window in APP.topLevelWidgets():
    window.close(); window.deleteLater()
QtCore.QCoreApplication.sendPostedEvents(None,QtCore.QEvent.DeferredDelete)
APP.processEvents(); gc.collect(); APP.quit()
print('EXPLICIT_QT_TEARDOWN_COMPLETED',flush=True)
sys.exit(int(result))
