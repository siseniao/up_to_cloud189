from getpass import getpass
from sys import exit as exit_cmd
from webbrowser import open_new_tab

from cloud189.api import Cloud189
from cloud189.api.models import FolderList

from cloud189.cli import config
from cloud189.cli.downloader import Downloader, Uploader
# from cloud189.cli.recovery import Recovery
from cloud189.cli.manager import global_task_mgr
from cloud189.cli.utils import *


class Commander:
    """网盘命令行"""

    def __init__(self):
        self._prompt = '> '
        self._disk = Cloud189()
        self._task_mgr = global_task_mgr
        self._dir_list = ''
        self._file_list = FolderList()
        self._path_list = FolderList()
        self._parent_id = -11
        self._parent_name = ''
        self._work_name = ''
        self._work_id = -11
        self._last_work_id = -11
        self._reader_mode = False
        self._reader_mode = config.reader_mode
        self._default_dir_pwd = ''

    @staticmethod
    def clear():
        clear_screen()

    @staticmethod
    def help():
        print_help()

    @staticmethod
    def update():
        check_update()

    def bye(self):
        if self._task_mgr.has_alive_task():
            info(f"有任务在后台运行, 退出请直接关闭窗口")
        else:
            exit_cmd(0)

    def exit(self):
        self.bye()

    def rmode(self):
        """适用于屏幕阅读器用户的显示方式"""
        choice = input("以适宜屏幕阅读器的方式显示(y): ")
        if choice and choice.lower() == 'y':
            config.reader_mode = True
            self._reader_mode = True
            info("已启用 Reader Mode")
        else:
            config.reader_mode = False
            self._reader_mode = False
            info("已关闭 Reader Mode")

    def cdrec(self):
        """进入回收站模式"""
        pass
        # rec = Recovery(self._disk)
        # rec.run()
        # self.refresh()

    def xghost(self):
        """扫描并删除幽灵文件夹"""
        pass
        # choice = input("需要清理幽灵文件夹吗(y): ")
        # if choice and choice.lower() == 'y':
        #     self._disk.clean_ghost_folders()
        #     info("清理已完成")
        # else:
        #     info("清理操作已取消")

    def refresh(self, dir_id=None):
        """刷新当前文件夹和路径信息"""
        dir_id = self._work_id if dir_id is None else dir_id
        self._file_list, self._path_list = self._disk.get_file_list(dir_id)
        self._prompt = '/'.join(self._path_list.all_name) + ' > '
        self._last_work_id = self._work_id
        self._work_name = self._path_list[-1].name
        self._work_id = self._path_list[-1].id
        if dir_id != -11:  # 如果存在上级路径
            self._parent_name = self._path_list[-2].name
            self._parent_id = self._path_list[-2].id

    def login(self):
        """登录网盘"""
        if not config.cookie or self._disk.login_by_cookie(config.cookie) != Cloud189.SUCCESS:
            username = input('输入用户名:')
            password = getpass('输入密码:')
            code = self._disk.login(username, password)
            if code == Cloud189.NETWORK_ERROR:
                error("登录失败,网络连接异常")
                return None
            elif code == Cloud189.FAILED:
                error('登录失败,用户名或密码错误 :(')
                return None
            # 登录成功保存用户 cookie
            config.cookie = self._disk.get_cookie()
        self.refresh()


    def clogin(self):
        """使用 cookie 登录"""
        open_new_tab('https://cloud.189.cn')
        info("请设置 Cookie 内容:")
        c_login_user = input("COOKIE_LOGIN_USER=")
        if not c_login_user:
            error("请输入正确的 Cookie 信息")
            return None
        cookie = {"COOKIE_LOGIN_USER": str(c_login_user)}
        if self._disk.login_by_cookie(cookie) == Cloud189.SUCCESS:
            config.cookie = cookie
            self.refresh()
        else:
            error("登录失败,请检查 Cookie 是否正确")

    def logout(self):
        """注销"""
        clear_screen()
        self._prompt = '> '
        self._disk.logout()
        self._file_list.clear()
        # self._dir_list.clear()
        self._path_list = ''
        self._parent_id = -11
        self._work_id = -11
        self._last_work_id = -11
        self._parent_name = ''
        self._work_name = ''
        config.cookie = None

    def ls(self, args):
        """列出文件(夹)"""
        fid = old_fid = self._work_id
        if args:
            if file := self._file_list.find_by_name(args[0]):
                if file.isFolder:
                    fid = file.id
                else:
                    error(f"{args[0]} 非文件夹，显示当前目录文件")
            else:
                error(f"{args[0]} 不存在，显示当前目录文件")
        if fid != old_fid:
            self._file_list, _ = self._disk.get_file_list(fid)
        if self._reader_mode:  # 方便屏幕阅读器阅读
            for file in self._file_list:
                print(f"{file.name}  大小:{get_file_size_str(file.size)}  上传时间:{file.time}  ID:{file.id}")
        else:  # 普通用户显示方式
            for file in self._file_list:
                star = '✦' if file.isStarred else '✧'
                print("# {0:<17}{1:<4}{2:<20}{3:>8}  {4}".format(
                    file.id, star, file.time, get_file_size_str(file.size), file.name))
        if fid != old_fid:
            self._file_list, _ = self._disk.get_file_list(old_fid)

    def cd(self, args):
        """切换工作目录"""
        dir_name = args[0]
        if not dir_name:
            info('cd .. 返回上级路径, cd - 返回上次路径, cd / 返回根目录')
        elif dir_name == '..':
            self.refresh(self._parent_id)
        elif dir_name == '/':
            self.refresh(-11)
        elif dir_name == '-':
            self.refresh(self._last_work_id)
        elif dir_name == '.':
            pass
        elif folder := self._file_list.find_by_name(dir_name):
            self.refresh(folder.id)
        else:
            error(f'文件夹不存在: {dir_name}')

    def mkdir(self, args):
        """创建文件夹"""
        if not args:
            info('参数：新建文件夹名')
        for name in args:
            if self._file_list.find_by_name(name):
                error(f'文件夹已存在: {name}')
                continue
            r = self._disk.mkdir(self._work_id, name)
            if r.code == Cloud189.SUCCESS:
                print(f"{name} ID: ", r.id)
            else:
                error(f'创建文件夹 {name} 失败!')
                continue

    def rm(self, args):
        """删除文件(夹)"""
        if not args:
            info('参数：删除文件夹(夹)名')
            return
        for name in args:
            if file := self._file_list.find_by_name(name):
                self._disk.delete_by_id(file.id)
            else:
                error(f"无此文件：{name}")
        self.refresh()

    def rename(self, args):
        """重命名文件(夹)"""
        info('目前还未完成！')
        return
        name = args[0].strip(' ')
        if not name:
            info('参数：原文件名 [新文件名]')
        elif file := self._file_list.find_by_name(name):
            new = args[1].strip(' ') if len(args) == 2 else input(f"请输入新文件名：")
            code = self._disk.rename(file.id, new)
            if code == Cloud189.SUCCESS:
                self.refresh()
            elif code == Cloud189.NETWORK_ERROR:
                error(f'网络错误，请重试！')
            else:
                error(f'失败，未知错误！')
        else:
            error(f'没有找到文件(夹): {name}')

    def mv(self, args):
        """移动文件或文件夹"""
        info('目前还未完成！')
        return
        name = args[0]
        if not name:
            info('参数：文件名 [新文件夹名]')
        if len(args) >= 2:
            new = args[1]

        if file := self._file_list.find_by_name(name):
            taskInfo = {"fileId": str(file.id),
                        "srcParentId": str(file.pid),
                        "fileName": file.name,
                        "isFolder": 1 if file.isFolder else 0 }

        else:
            error(f"文件(夹)不存在: {name}")
            return None
        # ---- TODO
        path_list = self._disk.get_move_paths()
        path_list = {'/'.join(path.all_name): path[-1].id for path in path_list}
        choice_list = list(path_list.keys())
        '''
        def _condition(typed_str, choice_str):
            path_depth = len(choice_str.split('/'))
            # 没有输入时, 补全 Cloud189,深度 1
            if not typed_str and path_depth == 1:
                return True
            # Cloud189/ 深度为 2,补全同深度的文件夹 Cloud189/test 、Cloud189/txt
            # Cloud189/tx 应该补全 Cloud189/txt
            if path_depth == len(typed_str.split('/')) and choice_str.startswith(typed_str):
                return True

        set_completer(choice_list, condition=_condition)
        choice = input('请输入路径(TAB键补全) : ')
        if not choice or choice not in choice_list:
            error(f"目标路径不存在: {choice}")
            return None
        folder_id = path_list.get(choice)
        if is_file:
            if self._disk.move_file(fid, folder_id) == Cloud189.SUCCESS:
                self._file_list.pop_by_id(fid)
            else:
                error(f"移动文件到 {choice} 失败")
        else:
            if self._disk.move_folder(fid, folder_id) == Cloud189.SUCCESS:
                self._dir_list.pop_by_id(fid)
            else:
                error(f"移动文件夹到 {choice} 失败")
        '''

    def down(self, args):
        """自动选择下载方式"""
        for item in args:
            if file := self._file_list.find_by_name(item):
                downloader = Downloader(self._disk)
                if file.isFolder:
                    print("暂不支持下载文件夹！")
                    continue
                else:
                    path = '/'.join(self._path_list.all_name) + '/' + item  # 文件在网盘的绝对路径
                    downloader.set_fid(file.id, is_file=True, f_path=path)
                    print("开始下载, 输入 jobs 查看下载进度...")
            else:
                error(f'文件(夹)不存在: {item}')
                continue
            # 提交下载任务
            self._task_mgr.add_task(downloader)

            # if arg.startswith('http'):
            #     downloader.set_url(arg)
            # elif file := self._file_list.find_by_name(arg):  # 如果是文件
            #     path = '/'.join(self._path_list.all_name) + '/' + arg  # 文件在网盘的绝对路径
            #     downloader.set_fid(file.id, is_file=True, f_path=path)
            # elif folder := self._dir_list.find_by_name(arg):  # 如果是文件夹
            #     path = '/'.join(self._path_list.all_name) + '/' + arg + '/'  # 文件夹绝对路径, 加 '/' 以便区分
            #     downloader.set_fid(folder.id, is_file=False, f_path=path)

    def jobs(self, args):
        """显示后台任务列表"""
        if not args:
            self._task_mgr.show_tasks()
        for arg in args:
            if arg.isnumeric():
                self._task_mgr.show_detail(int(arg))
            else:
                self._task_mgr.show_tasks()

    def upload(self, args):
        """上传文件(夹)"""
        if not args:
            info('参数：文件路径')
        for path in args:
            path = path.strip('\"\' ')  # 去除直接拖文件到窗口产生的引号
            if not os.path.exists(path):
                error(f'该路径不存在哦: {path}')
                continue
            uploader = Uploader(self._disk)
            if os.path.isfile(path):
                uploader.set_upload_path(path, is_file=True)
            else:
                uploader.set_upload_path(path, is_file=False)
            uploader.set_target(self._work_id, self._work_name)
            self._task_mgr.add_task(uploader)

    def share(self, args):
        """分享文件"""
        name = args[0]
        if not name:
            info('参数：需要分享的文件 [1/2/3] [1/2]')
            return
        if file := self._file_list.find_by_name(name):
            et = args[1] if len(args) >= 2 else None
            ac = args[2] if len(args) >= 3 else None
            result = self._disk.share_file(file.id, et, ac)
            if result.code == Cloud189.SUCCESS:
                print("-" * 50)
                print(f"{'文件夹名' if file.isFolder else '文件名  '} : {name}")
                print(f"上传时间 : {file.time}")
                if not file.isFolder:
                    print(f"文件大小 : {get_file_size_str(file.size)}")
                print(f"分享链接 : {result.url}")
                print(f"提取码   : {result.pwd or '无'}")
                if result.et == '1':
                    time = '1天'
                elif result.et == '2':
                    time = '7天'
                else:
                    time = '永久'
                print(f"有效期   : {time}")
                print("-" * 50)
            else:
                error('获取文件(夹)信息出错！')
        else:
            error(f"文件(夹)不存在: {name}")

    # def passwd(self, name):
    #     """设置文件(夹)提取码"""
    #     if file := self._file_list.find_by_name(name):  # 文件
    #         inf = self._disk.get_share_info(file.id, True)
    #         new_pass = input(f'修改提取码 "{inf.pwd or "无"}" -> ')
    #         if 2 <= len(new_pass) <= 6:
    #             if new_pass == 'off': new_pass = ''
    #             if self._disk.set_passwd(file.id, str(new_pass), True) != Cloud189.SUCCESS:
    #                 error('设置文件提取码失败')
    #             self.refresh()
    #         else:
    #             error('提取码为2-6位字符,关闭请输入off')
    #     elif folder := self._dir_list.find_by_name(name):  # 文件夹
    #         inf = self._disk.get_share_info(folder.id, False)
    #         new_pass = input(f'修改提取码 "{inf.pwd or "无"}" -> ')
    #         if 2 <= len(new_pass) <= 12:
    #             if new_pass == 'off': new_pass = ''
    #             if self._disk.set_passwd(folder.id, str(new_pass), False) != Cloud189.SUCCESS:
    #                 error('设置文件夹提取码失败')
    #             self.refresh()
    #         else:
    #             error('提取码为2-12位字符,关闭请输入off')
    #     else:
    #         error(f'文件(夹)不存在: {name}')

    # def desc(self, name):
    #     """设置文件描述"""
    #     if file := self._file_list.find_by_name(name):  # 文件
    #         inf = self._disk.get_share_info(file.id, True)
    #         print(f"当前描述: {inf.desc or '无'}")
    #         desc = input(f'修改为 -> ')
    #         if not desc:
    #             error(f'文件描述不允许为空')
    #             return None
    #         if self._disk.set_desc(file.id, str(desc), True) != Cloud189.SUCCESS:
    #             error(f'文件描述修改失败')
    #         self.refresh()
    #     elif folder := self._dir_list.find_by_name(name):  # 文件夹
    #         inf = self._disk.get_share_info(folder.id, False)
    #         print(f"当前描述: {inf.desc}")
    #         desc = input(f'修改为 -> ') or ''
    #         if self._disk.set_desc(folder.id, str(desc), False) == Cloud189.SUCCESS:
    #             if len(desc) == 0:
    #                 info('文件夹描述已关闭')
    #         else:
    #             error(f'文件夹描述修改失败')
    #         self.refresh()
    #     else:
    #         error(f'文件(夹)不存在: {name}')

    def setpath(self):
        """设置下载路径"""
        print(f"当前下载路径 : {config.save_path}")
        path = input('修改为 -> ').strip("\"\' ")
        if os.path.isdir(path):
            config.save_path = path
        else:
            error('路径非法,取消修改')

    def setsize(self):
        """设置上传限制"""
        print(f"当前限制(MB): {config.max_size}")
        max_size = input('修改为 -> ')
        if not max_size.isnumeric():
            error("请输入大于 100 的数字")
            return None
        if self._disk.set_max_size(int(max_size)) != Cloud189.SUCCESS:
            error("设置失败，限制值必需大于 100")
            return None
        config.max_size = int(max_size)

    def setdelay(self):
        """设置大文件上传延时"""
        print("大文件数据块上传延时范围(秒), 如: 0 60")
        print(f"当前配置: {config.upload_delay}")
        tr = input("请输入延时范围: ").split()
        if len(tr) != 2:
            error("格式有误!")
            return None
        tr = (int(tr[0]), int(tr[1]))
        self._disk.set_upload_delay(tr)
        config.upload_delay = tr

    def setpasswd(self):
        """设置文件(夹)默认上传密码"""
        print("关闭提取码请输入 off")
        print(f"当前配置: 文件: {config.default_file_pwd or '无'}, 文件夹: {config.default_dir_pwd or '无'}")
        file_pwd = input("设置文件默认提取码(2-6位): ")
        if 2 <= len(file_pwd) <= 6:
            config.default_file_pwd = '' if file_pwd == 'off' else file_pwd
        dir_pwd = input("设置文件夹默认提取码(2-12位): ")
        if 2 <= len(dir_pwd) <= 12:
            config.default_dir_pwd = '' if dir_pwd == 'off' else dir_pwd
        info(f"修改成功: 文件: {config.default_file_pwd or '无'}, 文件夹: {config.default_dir_pwd or '无'}, 配置将在下次启动时生效")

    def run_one(self, cmd, arg):
        no_arg_cmd = ['bye', 'exit', 'cdrec', 'clear', 'clogin', 'help', 'login', 'logout', 'refresh', 'rmode', 'setpath',
                      'setsize', 'update', 'xghost', 'setdelay', 'setpasswd']
        cmd_with_arg = ['ls', 'cd', 'desc', 'down', 'jobs', 'mkdir', 'mv', 'passwd', 'rename', 'rm', 'share', 'upload']

        if cmd in no_arg_cmd:
            getattr(self, cmd)()
        elif cmd in cmd_with_arg:
            getattr(self, cmd)(arg)
    
    def handle_args(self, args: str) -> list:
        is_file = 0
        real_file_name = ""
        real_file_list = []
        file_list = args.split(" ")
        for file in file_list:
            if "." not in file:
                real_file_name += file + " "
                is_file = 0
            else:
                if not is_file:
                    real_file_name += file
                    real_file_list.append(real_file_name)
                    real_file_name = ""
                else:
                    is_file = 1
                    real_file_list.append(file)
        return real_file_list

    def run(self):
        """处理一条用户命令"""
        no_arg_cmd = ['bye', 'exit', 'cdrec', 'clear', 'clogin', 'help', 'login', 'logout', 'refresh', 'rmode', 'setpath',
                      'setsize', 'update', 'xghost', 'setdelay', 'setpasswd']
        cmd_with_arg = ['ls', 'cd', 'desc', 'down', 'jobs', 'mkdir', 'mv', 'passwd', 'rename', 'rm', 'share', 'upload']

        choice_list = self._file_list.all_name  # + self._dir_list.all_name
        cmd_list = no_arg_cmd + cmd_with_arg
        set_completer(choice_list, cmd_list=cmd_list)

        try:
            args = input(self._prompt).split(' ', 1)
            if len(args) == 0:
                return None
        except KeyboardInterrupt:
            print('')
            info('退出本程序请输入 bye 或 exit')
            return None
        # a = [i for i in args[1].split(' ')]
        # print(*args[1:], '====', a)
        cmd, args = (args[0], []) if len(args) == 1 else (args[0], self.handle_args(args[1]))  # 命令, 参数(可带有空格, 没有参数就设为空)

        if cmd in no_arg_cmd:
            getattr(self, cmd)()
        elif cmd in cmd_with_arg:
            getattr(self, cmd)(args)