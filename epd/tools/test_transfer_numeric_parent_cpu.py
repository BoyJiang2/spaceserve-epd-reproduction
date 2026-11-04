import importlib.util,time
from pathlib import Path
def cpu_worker(role,conn,run,deadline):
    while True:time.sleep(1)
if __name__=='__main__':
    spec=importlib.util.spec_from_file_location('numeric',Path(__file__).with_name('official_transfer_numeric.py'))
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
    m.worker=cpu_worker
    m.main()
