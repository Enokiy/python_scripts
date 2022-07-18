#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ** Author: ssooking
import os
import argparse
import sys

if sys.version_info < (3,0):
    from pyinotify2 import WatchManager, Notifier,ProcessEvent
    from pyinotify2 import IN_ACCESS,IN_MODIFY,IN_ATTRIB,IN_CLOSE_WRITE,IN_OPEN,IN_MOVED_FROM,IN_MOVED_TO,IN_CREATE,IN_DELETE
else:
    from pyinotify3 import WatchManager, Notifier,ProcessEvent
    from pyinotify3 import IN_ACCESS,IN_MODIFY,IN_ATTRIB,IN_CLOSE_WRITE,IN_OPEN,IN_MOVED_FROM,IN_MOVED_TO,IN_CREATE,IN_DELETE

class EventHandler(ProcessEvent):
        """事件处理"""
        # 创建事件
        def process_IN_CREATE(self, event):
            print("[!] Create : " + event.pathname)
            # DeleteFileOrDir(event.pathname)

        # 删除事件
        def process_IN_DELETE(self, event):
            print("[!] Delete : " + event.pathname)

        #文件属性被修改，如chmod、chown命令
        def process_IN_ATTRIB(self, event):
            print("[!] Attribute been modified:" + event.pathname)

        #文件被移来，如mv、cp命令
        def process_IN_MOVED_TO(self, event):
            if hasattr(event,'src_pathname'):
                print("[!] Moved \t" + event.src_pathname + " ->  " + event.pathname)
            else:
                print("[!] Moved \t" + "unknown " + " ->  " + event.pathname)
            # DeleteFileOrDir(event.pathname)

        def process_IN_OPEN(self,event):
            print("[!] Open : " + event.pathname)
            pass

        def process_IN_CLOSE_WRITE(self,event):
            print("[!] Write : " + event.pathname)
            pass





def DeleteFileOrDir(target):
    if os.path.isdir(target):
        fileslist = os.listdir(target)
        for files in fileslist:
            DeleteFileOrDir(target + "/" + files)
        try:
            os.rmdir(target)
            print("     >>> Delete directory successfully: " + target)
        except:
            print("     [-] Delete directory failed: " + target)

    if os.path.isfile(target):
        try:
            os.remove(target)
            print("     >>> Delete file successfully" + target)
        except:
            print("     [-] Delete file filed:  " + target)


def Monitor(path):
        wm = WatchManager()
        mask = IN_ACCESS|IN_MODIFY|IN_ATTRIB|IN_CLOSE_WRITE|IN_OPEN|IN_MOVED_FROM|IN_MOVED_TO|IN_CREATE|IN_DELETE
        notifier = Notifier(wm, EventHandler())
        wm.add_watch(path, mask,rec=True)
        print('[+] Now Starting Monitor:  %s'%(path))
        while True:
                try:
                        notifier.process_events()
                        if notifier.check_events():
                                notifier.read_events()
                except KeyboardInterrupt:
                        notifier.stop()
                        break
                        
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        usage="%(prog)s -w [path]",
        description=('''
            Introduce：Simple File Monitor!  by ssooking''')
    )
    parser.add_argument('-w','--watch',action="store",dest="path",default="/var/www/html/",help="directory to watch,default is /var/www/html/")
    args=parser.parse_args()
    Monitor(args.path)