import Utls
from pathlib import Path
import time

Utls.clear_screen()
print(Utls.Fore.YELLOW + "网易我的世界基岩版调试器\n部分api需要使用WPFLauncher_Hook,需要确保安装且启动Web服务器")
time.sleep(1)
SettingJson = Utls.load_settings(Path(__file__).resolve().parent)


def main_menu():
    modules_dir = Utls.list_modules_root(__file__)
    if not modules_dir.exists():
        print(Utls.Fore.RED + f"未找到 Modules 目录: {modules_dir}")
        return

    while True:
        Utls.clear_screen()
        categories = [p.name for p in Utls.sorted_dirs(modules_dir)]
        if not categories:
            print(Utls.Fore.RED + 'Modules 下没有分类文件夹。')
            return

        sel = Utls.choose_from_list(
            '选择分类> ', categories, allow_back=False, allow_exit=True,
            header=Utls.Fore.YELLOW + '== 主页面: 请选择一个分类，输入对应数字进入；输入 exit 退出 =='
        )
        if sel == 'exit':
            print(Utls.Fore.GREEN + '退出程序')
            return

        cat_name = categories[sel]
        cat_path = modules_dir / cat_name

        py_files = Utls.sorted_py_files(cat_path)
        if not py_files:
            print(Utls.Fore.RED + '该分类下没有 .py 文件。按回车返回。')
            input()
            continue

        while True:
            Utls.clear_screen()
            names = [p.name for p in py_files]
            sel2 = Utls.choose_from_list(
                '选择脚本> ', names, allow_back=True, allow_exit=False,
                header=Utls.Fore.YELLOW + f'== 分类: {cat_name} — 请选择要运行的 .py 文件 =='
            )
            if sel2 == 'back':
                break
            path_to_run = py_files[sel2]
            Utls.run_py_file(path_to_run)
            print(Utls.Fore.GREEN + '脚本执行完毕，5秒后返回主页面...')
            time.sleep(5)
            break


if __name__ == '__main__':
    try:
        main_menu()
    except KeyboardInterrupt:
        print('\n' + Utls.Fore.GREEN + '已中断，退出。')
