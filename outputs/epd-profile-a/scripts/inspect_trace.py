"""Read-only SQLite inventory; CPU ranges alone do not establish GPU causality."""
import json
import sqlite3
import sys

connection = sqlite3.connect('file:' + sys.argv[1] + '?mode=ro', uri=True)
tables = {row[0] for row in connection.execute("select name from sqlite_master where type='table'")}
for table in sorted(tables):
    if table in {'NVTX_EVENTS', 'StringIds', 'TARGET_INFO_GPU'} or table.startswith('CUPTI_ACTIVITY_KIND_'):
        print(table, connection.execute(f'select count(*) from "{table}"').fetchone()[0])
        if table in {'NVTX_EVENTS', 'CUPTI_ACTIVITY_KIND_KERNEL', 'CUPTI_ACTIVITY_KIND_RUNTIME', 'TARGET_INFO_GPU'}:
            print('columns', [row[1] for row in connection.execute(f'pragma table_info("{table}")')])
if 'CUPTI_ACTIVITY_KIND_KERNEL' in tables:
    print('kernel groups', connection.execute('select deviceId,globalPid,count(*),min(start),max(end) from CUPTI_ACTIVITY_KIND_KERNEL group by deviceId,globalPid').fetchall())
if 'NVTX_EVENTS' in tables:
    print('nvtx samples', connection.execute('select start,end,eventType,globalTid,text from NVTX_EVENTS where text is not null limit 12').fetchall())
connection.close()
