#!/usr/bin/python
# coding=utf-8

"""
Created on 2022-04-18
@author: enokiy

describe:
收集服务器上docker容器信息，并基于workdir打包进程目录，下载到本地
"""
import json
import os

from info_collector.common_task import main
from info_collector.process_info_collector import SSHTask

mount_blaklist = ['/', '/proc', '/sys', '/run/docker.sock', '/var/run/docker.sock']
cap_blanklist = ['SYS_ADMIN', 'CAP_SYS_ADMIN','CAP_SYS_CHROOT','SYS_CHROOT','SYS_MODULE','CAP_SYS_MODULE',' CAP_SYS_PTRACE','SYS_PTRACE', 'DAC_READ_SEARCH']
download_file = False


class ContainerTask(SSHTask):
    def __init__(self, ip, username, password, root_pwd, shared_queue, port=22):
        SSHTask.__init__(self, ip, username, password, root_pwd, shared_queue, port=22)
        self.infos = dict()

    def get_infos(self):
        self.get_container_infos()

    def get_container_infos(self):
        print('=' * 20, 'start get %s\'s container info ' % self.ip, '=' * 20, '\n')
        all_cids = self.exec_command('su -c "docker ps -aq --filter \'status=running\'"').strip().split('\n')
        for cid in all_cids:
            cmd = 'su -c "docker inspect -f \'{{json .}}\' %s" root' % cid
            output = self.exec_command(cmd).strip()
            output_json = json.loads(output)
            is_prived = self._check_privileged(output_json)
            danger_mount = self._check_mount(output_json)
            danger_cap = self._check_capability(output_json)
            network_mode = self._check_network_mode(output_json)
            key = self.ip + '_' + output_json['Name']
            self.infos[key] = {"HostIP": self.ip, "ID": output_json['Id'], "Name": output_json['Name'],
                               "Hostname": output_json['Config']['Hostname'], "Path": output_json['Path'],
                               "Args": output_json['Args'], "Pid": output_json['State']['Pid'],
                               "WorkingDir": output_json['Config']['WorkingDir'],
                               "image": output_json['Image'],
                               "is_prived": is_prived, "danger_mount": danger_mount,
                               "danger_cap": danger_cap,
                               "network_mode": network_mode}
            if download_file:
                self._docker_file_download(cid=output_json['Id'],name=output_json['Config']['Hostname'],path=output_json['Path'],workingDir=output_json['Config']['WorkingDir'])
        print('=' * 20, 'finished to  get %s\'s container info ' % self.ip, '=' * 20, '\n')

    def _check_capability(self, docker_info):
        docker_caps = docker_info['HostConfig']['CapAdd']
        result = []
        if docker_caps:
            for cap in docker_caps:
                if cap in cap_blanklist:
                    result.append(cap)
        return result

    def _check_mount(self, docker_info):
        docker_mounts = docker_info["Mounts"]
        result = []
        if docker_mounts:
            for mount in docker_mounts:
                if mount in cap_blanklist:
                    result.append(
                        "Mount Type： {type}，Host Dir：{source}，container Dir：{dest} \n".format(type=mount.type, source=mount.source,
                                                                               dest=mount.dest))
        return result

    def _check_privileged(self, docker_info):
        is_privd = docker_info['HostConfig']['Privileged']
        return is_privd

    def _check_network_mode(self, docker_info):
        return docker_info['HostConfig']['NetworkMode']

    def _docker_save(self, image_id, image_name):
        self.exec_command(
            'su -c "docker save {id} > /tmp/{name}.tar&&chown {username}: /tmp/{name}" root'.format(id=image_id,
                                                                                                    name=image_name,
                                                                                                    username=self.username))

    def _docker_file_download(self, cid, name, path, workingDir):
        if  '/pause' == path:
            return
        # todo get  cwd and set workdir

        exec_cmd = 'su -c \'docker exec -u root {cid} bash -c "tar cvf /tmp/{name}.tar {workingDir} "\' root'.format(cid=cid,name=name,workingDir=workingDir)
        print(exec_cmd)
        result = self.exec_command(exec_cmd).strip()
        if 'exec failed' in result:
            return
        cp_cmd = 'su -c "docker cp {cid}:/tmp/{name}.tar /tmp &&chown {username}: /tmp/{name}.tar" root'.format(cid=cid,name=name,username=self.username)
        self.exec_command(cp_cmd)
        print('a'*20)
        self.download_file('/tmp/{name}.tar'.format(name=name), os.path.join('D:\\tmp\\',name+'.tar'))
        self.exec_command('su -c \'docker exec -u root {cid} bash -c "rm -rf /tmp/{name}.tar"\' root'.format(cid=cid,name=name))
        self.exec_command('rm -rf /tmp/{name}.tar')


if __name__ == '__main__':
    servers = [

    ]
    output_file = 'container_info.csv'
    headers = ['HostIP', 'ID', 'Name', 'Hostname', 'Path', 'Args', 'Pid', 'image', 'is_prived', 'danger_mount',
               'danger_cap', 'network_mode', 'WorkingDir']

    main(servers, ContainerTask, output_file, headers)
