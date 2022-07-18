#!/usr/bin/python
# coding=utf-8

"""
Created on 2022-04-14
@author: enokiy

说明：
该脚本的功能为：使用普通用户通过ssh连接远程服务器进行信息收集，收集的信息包括;
进程ID，名称，用户，监听的端口，启动命令，进程环境变量.

使用方法:
1.修改脚本中的servers, 每个server的形式为(ip,name,pwd,root_pwd)
"""

import re

from info_collector.common_task import SSHTask, OutputTask, main


class ProcInfoTask(SSHTask):
    def __init__(self, ip, username, password, root_pwd, shared_queue, port=22):
        SSHTask.__init__(self, ip, username, password, root_pwd, shared_queue, port=22)

    def get_infos(self):
        self.get_proc_infos()

    def get_proc_infos(self):

        """get process infos by executing netstat and ps command"""
        print('=' * 20, 'start get %s\'s process info ' % self.ip, '=' * 20, '\n')

        netstat_cmd = r"netstat -nlptu|awk -v OFS=',' '{if($7!=null){print $1,$4,$7}else{print $1,$4,$6}}'|grep -v " \
                      r"'Proto'|grep -v 'Active' "
        if self.username != 'root':
            netstat_cmd = "su -c \"netstat -nlptu\" root|awk -v OFS=',' '{if($7!=null){print $1,$4,$7}else{print $1," \
                          "$4,$6}}'|grep -v 'Proto'|grep -v 'Active' "

        netstat_output_str = self.exec_command(netstat_cmd)
        self._process_netstat(netstat_output_str)
        self._get_pid_user_cmd_info()
        print('=' * 20, 'finished to  get %s\'s process info ' % self.ip, '=' * 20, '\n')

    def _process_netstat(self, netstat_result):
        netstat_output = netstat_result.split('\n')  # \r\n or \n??
        for line in netstat_output:
            if (not line) or (not line.startswith('tcp') and not line.startswith('udp')):
                continue

            proto, ip_port, pid_name = tuple([i for i in line.split(',') if i != ''])

            pid = ''
            name = ''

            if re.match('.*/.*', pid_name):  # in some case,show - instead of pid/name
                pid, name = tuple(pid_name.split('/'))

            if pid_name in list(self.infos.keys()):
                self.infos[pid_name]['LISTEN'].append(proto + ' ' + ip_port)
            else:
                self.infos[pid_name] = {'PID': pid, 'NAME': name, 'LISTEN': [proto + ' ' + ip_port], 'USER': '',
                                        'CMD': '', 'ENV': '', 'HostIP': self.ip}

    def _get_pid_user_cmd_info(self):
        for proc_info in list(self.infos.values()):
            pid = proc_info['PID']
            if pid == '1' or pid == '':
                continue
            get_proc_user_cmd = 'ps --no-headers -o user -p {pid}|grep -v \'USER\''.format(pid=pid)
            get_proc_cmdline_cmd = 'cat /proc/{pid}/cmdline'.format(pid=pid)
            get_proc_env_cmd = 'cat /proc/{pid}/environ'.format(pid=pid)

            proc_info['USER'] = self.exec_command(get_proc_user_cmd).strip()
            proc_info['CMD'] = self.exec_command(get_proc_cmdline_cmd).strip()
            proc_info['ENV'] = self.exec_command(get_proc_env_cmd).strip()





if __name__ == '__main__':
    servers = [('ip', 'username', 'password', 'rootPassword'),

               ]
    output_file = 'process_info.csv'
    headers = ['HostIP', 'NAME', 'PID', 'LISTEN', 'USER', 'CMD',  'ENV']
    main(servers,ProcInfoTask,output_file,headers)
