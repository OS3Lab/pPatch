#!/bin/bash

# 获取第一个变量
variable=$1

use_config=$2

# 定义三个命令，使用该变量
if [[ $use_config == "true" ]]; then
  command1="ppatch auto /home/laboratory/workspace/archive/patches/poc_$variable.patch -o ../6.1-result/$variable.patch -c /home/laboratory/workspace/exps/ppatch/example_extra_config.json"
else
  command1="ppatch auto /home/laboratory/workspace/archive/patches/poc_$variable.patch -o ../6.1-result/$variable.patch"
fi

command2="patch -p 1 -F 3 -i ../6.1-result/$variable.patch"
command3=" patch -R -p 1 -F 3 -f -i /home/laboratory/workspace/archive/patches/poc_$variable.patch"

# 执行第一个命令并检查返回值
$command1
if [ $? -ne 0 ]; then
  echo "命令1执行失败，退出脚本。"
  exit 1
fi
read -p "命令1执行成功，按任意键继续..."

# 执行第二个命令并检查返回值
$command2
if [ $? -ne 0 ]; then
  echo "命令2执行失败，退出脚本。"
  exit 1
fi
read -p "命令2执行成功，按任意键继续..."

# 执行第三个命令并检查返回值
$command3
if [ $? -ne 0 ]; then
  echo "命令3执行失败，退出脚本。"
  exit 1
fi
read -p "命令3执行成功，按任意键继续..."

git diff > $variable.patch

scp pride:/mnt/cd7/ppatch_autoset/auto_linux_6.9.5_back/exps/poc_$variable/linux_6_lts/x86_64/linux_6_lts_kernel/upper_dir/.config .config.$variable

read -p "patch 生成与 config 下载结束，按任意键继续..."
