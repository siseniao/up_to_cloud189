import os.path
import sys, configparser
from cloud189.cli.cli import Commander
import copy

g_dict_curr = dict()
g_dict_pre = dict()


class AppConfig:
    def __init__(self):
        self.user_name = ''
        self.password = ''
        self.up_list = list()

    def load_ini_config(self):
        conf = configparser.ConfigParser()
        curr_dir = os.path.dirname(os.path.realpath(__file__))
        path = os.path.join(curr_dir, 'uploader.ini')
        conf.read(filenames=path, encoding='utf-8')
        self.user_name = conf['Login']['UserName']
        self.password = conf['Login']['Password']

        files = conf['Files']['FileList']
        list_uploads = files.split(';')
        for uploads in list_uploads:
            src_dst = uploads.split(',')
            if len(src_dst) < 2:
                continue
            self.up_list.append(list(src_dst))


def load_mt_file():
    try:
        with open('file_mt.txt', "r") as f:
            for mt_line in iter(lambda: f.readline(), ""):
                list_line = mt_line.split('=')
                if len(list_line) != 2:
                    continue
                g_dict_pre[list_line[0].strip()] = list_line[1].strip()
    except Exception as e:
        print(e)
        pass


def save_mt_file(files_dict: dict):
    if files_dict is None:
        return
    try:
        with open('file_mt.txt', "w") as f:
            for path_md5, file_mt, in files_dict.items():
                f.write(str(path_md5) + "=" + str(file_mt) + '\n')

    except Exception as e:
        print(e)
        pass


def upload_callback(file_name, total_size, now_size, msg=''):
    if msg != 'file_path':
        return True
    file_stats = os.stat(file_name)
    file_mtime = str(file_stats.st_mtime)
    g_dict_curr[file_name] = file_mtime
    not_same = True
    if file_name in g_dict_pre:
        if g_dict_pre[file_name] == file_mtime:
            not_same = False
        g_dict_pre.pop(file_name)

    return not_same


def upload_files_to_cloud():
    ini = AppConfig()
    ini.load_ini_config()
    load_mt_file()

    commander = Commander()

    commander.set_upload_callback(upload_callback)
    commander.login(['--auto', ini.user_name, ini.password])
    commander.sign(['--all'])
    for src_dst in ini.up_list:
        if not os.path.exists(src_dst[0]):
            print("Local path {} not exist!".format(src_dst[0]))
            continue
        if not commander.cd([src_dst[1]]):
            continue
        commander.upload(['--force', '--nodir', src_dst[0]])

    save_mt_file(g_dict_curr)
    # for src_dst in ini.up_list:
    #     for file, mtime in g_dict_pre.items():
    #         if file.startswith(src_dst[0]):
    #             file_remove = copy.deepcopy(file)
    #             file_remove.replace(src_dst[0], src_dst[1])
    #             file_remove.replace('\\', '/')
    #             commander.rm([file_remove])
    #             g_dict_pre.pop(file)


if __name__ == '__main__':
    try:
        upload_files_to_cloud()
    except Exception as e:
        print(e)

