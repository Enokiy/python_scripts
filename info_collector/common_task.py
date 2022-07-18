#!/usr/bin/python
# coding=utf-8

"""
Created on 2022-04-18
@author: enokiy

describe:
SSHTask: 建立一个远程连接，并执行命令。如果是以普通用户执行命令，需要将命令设置为su -c “cmd”的形式；命令执行的结果是以proc[key] ={a1:b1,a2:b2,a3:b3,a4:b4}这种格式，其中a1，a2, a3, a4将与
OoutputTask中的header对应，否则无法将执行结果正确写入文件；
OutputTask：将SSHTask执行的结果写入csv文件，需要提供的输入：写入的文件名和header，
"""
import csv
import datetime
import re
import threading
import time
from queue import Queue
from threading import Thread
import paramiko

G_SSH_LOCK = threading.RLock()
FINISHED_SIGNAL = '-----finished now ------'


class SSHTask(Thread):
    def __init__(self, ip, username, password, root_pwd, shared_queue, port=22):
        Thread.__init__(self, name="thread_%s" % ip)
        self.ip = ip.strip()
        self.port = port
        self.username = username.strip()
        self.password = password.strip()
        self.root_pwd = root_pwd.strip()
        self.shared_queue = shared_queue
        self.infos = dict()
        self.client = None

    def run(self):
        # get a ssh client
        try:
            G_SSH_LOCK.acquire()
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                client.connect(self.ip, port=self.port, username=self.username, password=self.password, timeout=10,
                               auth_timeout=15, banner_timeout=5)
                self.client = client
            except Exception as e:
                raise Exception("!" * 20 + "error,connect %s failed,error info: %s" % (self.ip, str(e)) + "!" * 20)

            try:
                with self.client:
                    self.get_infos()
                    if self.shared_queue is not None and len(self.infos.items()) != 0:
                        self.shared_queue.put((self.ip, self.infos), block=True)
            except Exception as e:
                raise Exception("~" * 20 + "error,handle collect info task failed on %s ,error info: %s" % (
                    self.ip, str(e)) + "~" * 20)
        except Exception as e:
            print(str(e))
        finally:
            G_SSH_LOCK.release()
            self.shared_queue.put((self.ip, FINISHED_SIGNAL), block=True)

    def get_infos(self):
        """
        override in the subclass to implement specific service code.
        output: infos[key] ={a1:b1,a2:b2,a3:b3,a4:b4}
        """
        pass

    def exec_command(self, cmd):
        try:
            buf = ''
            if cmd.startswith('su -c'):
                # ssh_shell = self.client.invoke_shell()
                # ssh_shell.sendall(cmd + '\n')
                # time.sleep(0.5)
                # # input root pwd,
                # ssh_shell.sendall(self.root_pwd + '\n')
                # time.sleep(0.5)
                #
                # buf = ssh_shell.recv(10000).decode('ascii')
                # ssh_shell.close()

                stdin, stdout, stderr = self.client.exec_command(cmd)
                stdin.write(self.root_pwd + '\n')
                stdin.flush()
                buf = stdout.read().decode('ascii')
            else:
                _, stdout, _ = self.client.exec_command(cmd)
                buf = stdout.read().decode('ascii')

            return buf
        except Exception as e:
            raise Exception('@' * 20, 'execute %s on %s failed,reason: %s ~~~' % (cmd, self.ip, str(e)), '@' * 20)

    def _get_banner(self):
        ssh_shell = self.client.invoke_shell()
        time.sleep(0.5)
        data = ssh_shell.recv(2048).decode('ascii').split('\n')[-1]
        ssh_shell.close()
        return data

    def download_file(self,remote_path,local_path):
        sftp = self.client.open_sftp()
        sftp.get(remote_path,local_path)

        sftp.close()




class OutputTask(Thread):
    def __init__(self, output_file, headers, shared_queue, queue_size):
        Thread.__init__(self, name='output_thread')
        self.output_file = output_file
        self.shared_queue = shared_queue
        self.queue_size = queue_size
        self.headers = headers

    def run(self):
        with open(self.output_file, 'w') as csv_file:
            writer = csv.DictWriter(csv_file, self.headers)
            writer.writeheader()
            self._write_data(writer)

    def _write_data(self, writer):
        count = self.queue_size
        while count > 0:
            try:
                host, infos = self.shared_queue.get(block=True)
                if FINISHED_SIGNAL == infos:
                    count = count - 1
                    print('=' * 20, 'finished write %s\'s process info data into file ' % host, '=' * 20, '\n')
                    continue
                print('=' * 20, 'start write %s\'s process info data into file ' % host, '=' * 20, '\n')
                writer.writerows(infos.values())
            except Exception as e:
                e


def main(servers, task, output_file, headers):
    print('=' * 20, 'start collect infos  on all servers ', '=' * 20, '\n')
    start = datetime.datetime.now()

    result = Queue()
    for host in servers:
        if len(host) > 4:
            task(host[0], host[1], host[2], host[3], result, port=host[4]).start()
        else:
            task(host[0], host[1], host[2], host[3], result).start()

    queue_size = len(servers)
    output_task = OutputTask(output_file, headers, result, queue_size)
    output_task.start()
    output_task.join()

    end = datetime.datetime.now()
    times = (end - start).seconds

    print('=' * 20, 'finished collect infos  on all servers ,use total time: %d' % times, '=' * 20, '\n')
