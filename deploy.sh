#!/bin/bash
set -e

echo "=== AI 叙事跑团 - 部署脚本 ==="

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${YELLOW}安装 Docker...${NC}"
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    echo -e "${GREEN}Docker 安装完成${NC}"
fi

# 检查 .env
if [ ! -f .env ]; then
    echo -e "${YELLOW}.env 不存在，从模板创建...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}请编辑 .env 填入配置后重新运行${NC}"
    exit 1
fi

# 构建启动
echo -e "${GREEN}构建并启动服务...${NC}"
docker compose -f docker-compose.prod.yml up -d --build

echo -e "${GREEN}等待服务启动...${NC}"
sleep 10

# 初始化数据库
echo -e "${GREEN}初始化数据库...${NC}"
docker compose -f docker-compose.prod.yml exec -T backend alembic upgrade head

# 设置自动备份
echo -e "${GREEN}配置自动备份...${NC}"
(crontab -l 2>/dev/null; echo "0 3 * * * cd $(pwd) && docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U gameuser gamedb | gzip > /home/\$(whoami)/backups/db_\$(date +\%Y\%m\%d).sql.gz 2>/dev/null") | crontab -

IP=$(hostname -I | awk '{print $1}')
echo ""
echo -e "${GREEN}=== 部署完成 ===${NC}"
echo "前端: http://$IP"
echo "API:  http://$IP:8000"
echo "文档: http://$IP:8000/docs"
echo ""
echo "常用命令:"
echo "  日志: docker compose -f docker-compose.prod.yml logs -f"
echo "  重启: docker compose -f docker-compose.prod.yml restart"
echo "  停止: docker compose -f docker-compose.prod.yml down"
echo "  更新: git pull && docker compose -f docker-compose.prod.yml up -d --build"
