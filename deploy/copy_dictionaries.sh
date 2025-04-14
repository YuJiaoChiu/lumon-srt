#!/bin/bash

# 复制初始词典文件的脚本

# 检查源目录是否存在
if [ ! -d "../backend/dictionaries" ]; then
    echo "源词典目录不存在: ../backend/dictionaries"
    exit 1
fi

# 确保目标目录存在
mkdir -p dictionaries

# 复制词典文件
echo "复制词典文件..."
cp -r ../backend/dictionaries/* dictionaries/

# 设置权限
echo "设置权限..."
chmod -R 755 dictionaries

echo "词典文件复制完成！"
