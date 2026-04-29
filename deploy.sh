#!/bin/bash
set -e

# ============================================
# AI 叙事跑团游戏 - 一键部署脚本
# 仓库: https://github.com/xpxp23/airpg
# ============================================

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m'

COMPOSE_FILE="docker-compose.prod.yml"
BACKUP_DIR="/home/$(whoami)/backups"

MIRROR_MODE=false

log_info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()  { echo -e "${BLUE}[STEP]${NC} $1"; }

echo ""
echo "=========================================="
echo "   AI 叙事跑团游戏 - 一键部署"
echo "   https://github.com/xpxp23/airpg"
echo "=========================================="
echo ""

# 解析参数
for arg in "$@"; do
    case $arg in
        --mirror) MIRROR_MODE=true ;;
        --help|-h)
            echo "用法: ./deploy.sh [选项]"
            echo ""
            echo "选项:"
            echo "  --mirror    使用国内镜像源加速（Docker/apt/apk/npm/pip）"
            echo "  --help      显示帮助信息"
            exit 0
            ;;
    esac
done

# ----- 配置国内镜像 -----
setup_mirrors() {
    log_step "配置国内镜像源..."

    # 1. Docker 镜像加速
    if [ ! -f /etc/docker/daemon.json ] || ! grep -q "registry-mirrors" /etc/docker/daemon.json 2>/dev/null; then
        sudo mkdir -p /etc/docker
        sudo tee /etc/docker/daemon.json > /dev/null <<'DEOFE'
{
  "registry-mirrors": [
    "https://mirror.ccs.tencentyun.com",
    "https://docker.m.daocloud.io",
    "https://huecker.io"
  ]
}
DEOFE
        sudo systemctl daemon-reload
        sudo systemctl restart docker
        log_info "Docker 镜像加速已配置"
    else
        log_info "Docker 镜像加速已存在，跳过"
    fi

    # 2. 宿主机 apt 镜像（Debian/Ubuntu）
    if [ -f /etc/debian_version ]; then
        if ! grep -q "mirrors.aliyun.com" /etc/apt/sources.list 2>/dev/null; then
            CODENAME=$(. /etc/os-release && echo "$VERSION_CODENAME")
            if [ -n "$CODENAME" ]; then
                sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak.$(date +%s)
                sudo tee /etc/apt/sources.list > /dev/null <<EOF
deb https://mirrors.aliyun.com/debian/ ${CODENAME} main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian/ ${CODENAME}-updates main contrib non-free non-free-firmware
deb https://mirrors.aliyun.com/debian-security ${CODENAME}-security main contrib non-free non-free-firmware
EOF
                sudo apt-get update -qq
                log_info "宿主机 apt 镜像已配置 (${CODENAME})"
            fi
        else
            log_info "宿主机 apt 镜像已存在，跳过"
        fi
    fi

    # 3. 后端 Dockerfile: pip 镜像 + Debian apt 镜像
    if [ -f backend/Dockerfile ]; then
        # 创建 pip 配置
        mkdir -p backend/pip-conf
        cat > backend/pip-conf/pip.conf <<'EOF'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
EOF

        # 备份原 Dockerfile
        cp backend/Dockerfile backend/Dockerfile.bak 2>/dev/null || true

        # 重写 Dockerfile，注入 apt 镜像和 pip 镜像
        cat > backend/Dockerfile <<'DEOF'
FROM python:3.12-slim

WORKDIR /app

# 使用阿里云 Debian 镜像加速 apt
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list 2>/dev/null || true
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY pip-conf/pip.conf /etc/pip.conf
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
DEOF
        log_info "后端 Dockerfile 已配置 apt + pip 镜像"
    fi

    # 4. 前端 Dockerfile: npm 镜像 + Alpine apk 镜像
    if [ -f frontend/Dockerfile ]; then
        # 创建 npm 配置
        cat > frontend/.npmrc <<'EOF'
registry=https://registry.npmmirror.com
EOF

        # 备份原 Dockerfile
        cp frontend/Dockerfile frontend/Dockerfile.bak 2>/dev/null || true

        # 重写 Dockerfile，注入 apk 镜像和 npm 镜像
        cat > frontend/Dockerfile <<'DEOF'
FROM node:20-alpine AS builder

WORKDIR /app

# 使用阿里云 Alpine 镜像加速 apk
RUN sed -i 's|dl-cdn.alpinelinux.org|mirrors.aliyun.com|g' /etc/apk/repositories
RUN apk add --no-cache libc6-compat

COPY .npmrc ./
COPY package.json package-lock.json* ./
RUN npm ci

COPY . .
RUN npm run build

FROM node:20-alpine AS runner

WORKDIR /app

RUN sed -i 's|dl-cdn.alpinelinux.org|mirrors.aliyun.com|g' /etc/apk/repositories

ENV NODE_ENV=production

COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

EXPOSE 3000

CMD ["node", "server.js"]
DEOF
        log_info "前端 Dockerfile 已配置 apk + npm 镜像"
    fi

    log_info "国内镜像源配置完成"
}

if [ "$MIRROR_MODE" = true ]; then
    setup_mirrors
fi

# ----- 前置检查 -----

log_step "1/7 检查系统环境..."

# 检查操作系统
if [ -f /etc/os-release ]; then
    . /etc/os-release
    log_info "操作系统: $PRETTY_NAME"
else
    log_warn "无法检测操作系统，继续部署..."
fi

# 检查内存
TOTAL_MEM=$(free -m | awk '/^Mem:/{print $2}')
if [ "$TOTAL_MEM" -lt 3500 ]; then
    log_warn "内存不足 4GB (当前: ${TOTAL_MEM}MB)，可能影响性能，建议添加 swap"
    if [ ! -f /swapfile ]; then
        read -p "是否自动创建 4GB swap? [y/N] " CREATE_SWAP
        if [[ "$CREATE_SWAP" =~ ^[Yy]$ ]]; then
            log_info "创建 swap..."
            sudo fallocate -l 4G /swapfile
            sudo chmod 600 /swapfile
            sudo mkswap /swapfile
            sudo swapon /swapfile
            echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
            log_info "swap 创建完成"
        else
            log_warn "跳过 swap 创建，继续部署..."
        fi
    fi
fi

# 检查磁盘空间
AVAIL_DISK=$(df -BG . | awk 'NR==2{print $4}' | tr -d 'G')
if [ "$AVAIL_DISK" -lt 20 ]; then
    log_warn "磁盘空间不足 20GB (可用: ${AVAIL_DISK}GB)，可能导致构建失败"
else
    log_info "磁盘空间充足: ${AVAIL_DISK}GB"
fi
log_info "内存: ${TOTAL_MEM}MB"

# ----- 安装 Docker -----

log_step "2/7 检查 Docker..."

if ! command -v docker &> /dev/null; then
    log_warn "Docker 未安装，开始安装..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
    rm get-docker.sh
    log_info "Docker 安装完成"
    log_warn "请执行 'newgrp docker' 或重新登录后再次运行此脚本"
    exit 0
fi

if ! docker compose version &> /dev/null; then
    log_error "docker compose 不可用，请升级 Docker 到最新版本"
    exit 1
fi

DOCKER_VER=$(docker --version | awk '{print $3}' | tr -d ',')
COMPOSE_VER=$(docker compose version --short)
log_info "Docker: $DOCKER_VER, Compose: $COMPOSE_VER"

# ----- 配置环境变量 -----

log_step "3/7 检查环境变量..."

if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
        log_warn ".env 文件不存在，已从 .env.example 创建"
        echo ""
        echo "请编辑 .env 文件，至少修改以下必填项："
        echo "  - POSTGRES_PASSWORD  (数据库密码)"
        echo "  - AI_API_KEY         (AI API 密钥)"
        echo "  - AI_BASE_URL        (API 地址)"
        echo "  - JWT_SECRET_KEY     (JWT 密钥)"
        echo "  - NEXT_PUBLIC_API_URL(前端访问地址)"
        echo ""
        echo "编辑完成后重新运行: ./deploy.sh"
        exit 1
    else
        log_error ".env.example 文件不存在，请确认在项目根目录运行"
        exit 1
    fi
fi

# 检查必填项
source .env
MISSING=()
[ -z "$POSTGRES_PASSWORD" ] && MISSING+=("POSTGRES_PASSWORD")
[ -z "$AI_API_KEY" ] && MISSING+=("AI_API_KEY")
[ -z "$JWT_SECRET_KEY" ] || [ "$JWT_SECRET_KEY" = "your-super-secret-key-change-this" ] && MISSING+=("JWT_SECRET_KEY")

if [ ${#MISSING[@]} -gt 0 ]; then
    log_error ".env 中以下必填项未配置或使用了默认值："
    for item in "${MISSING[@]}"; do
        echo "  - $item"
    done
    echo ""
    echo "请编辑 .env 后重新运行: ./deploy.sh"
    exit 1
fi

log_info "环境变量检查通过"

# ----- 创建备份目录 -----

log_step "4/7 配置自动备份..."

mkdir -p "$BACKUP_DIR"

# 移除旧的备份任务（如果有）
crontab -l 2>/dev/null | grep -v "airpg.*backup" | crontab - 2>/dev/null || true

# 添加每日凌晨 3 点备份
BACKUP_CMD="0 3 * * * cd $(pwd) && docker compose -f $COMPOSE_FILE exec -T postgres pg_dump -U ${POSTGRES_USER:-gameuser} ${POSTGRES_DB:-gamedb} | gzip > $BACKUP_DIR/db_\$(date +\\%Y\\%m\\%d).sql.gz 2>/dev/null && find $BACKUP_DIR -name '*.sql.gz' -mtime +7 -delete"
(crontab -l 2>/dev/null; echo "$BACKUP_CMD") | crontab -

log_info "自动备份已配置（每天 03:00，保留 7 天）"

# ----- 拉取镜像 -----

log_step "5/7 拉取基础镜像..."

docker compose -f $COMPOSE_FILE pull --quiet postgres redis nginx 2>/dev/null || \
    docker compose -f $COMPOSE_FILE pull postgres redis nginx

log_info "基础镜像拉取完成"

# ----- 构建启动 -----

log_step "6/7 构建并启动服务..."

docker compose -f $COMPOSE_FILE up -d --build

echo ""
log_info "等待服务就绪..."
sleep 15

# 等待 postgres 就绪
RETRIES=0
until docker compose -f $COMPOSE_FILE exec -T postgres pg_isready -U ${POSTGRES_USER:-gameuser} -d ${POSTGRES_DB:-gamedb} &>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -gt 30 ]; then
        log_error "PostgreSQL 启动超时"
        docker compose -f $COMPOSE_FILE logs postgres
        exit 1
    fi
    sleep 2
done
log_info "PostgreSQL 就绪"

# 等待 redis 就绪
RETRIES=0
until docker compose -f $COMPOSE_FILE exec -T redis redis-cli ping &>/dev/null; do
    RETRIES=$((RETRIES + 1))
    if [ $RETRIES -gt 15 ]; then
        log_error "Redis 启动超时"
        exit 1
    fi
    sleep 2
done
log_info "Redis 就绪"

# ----- 初始化数据库 -----

log_step "7/7 初始化数据库..."

docker compose -f $COMPOSE_FILE exec -T backend alembic upgrade head 2>/dev/null || \
    log_warn "数据库迁移执行失败（如果是首次部署可能需要手动执行）"

# ----- 部署完成 -----

IP=$(hostname -I 2>/dev/null | awk '{print $1}' || curl -s ifconfig.me 2>/dev/null || echo "your-server-ip")

echo ""
echo "=========================================="
echo -e "   ${GREEN}部署完成!${NC}"
echo "=========================================="
echo ""
echo "  前端:   http://$IP"
echo "  API:    http://$IP:8000"
echo "  文档:   http://$IP:8000/docs"
if [ "$MIRROR_MODE" = true ]; then
    echo "  镜像:   已启用国内加速源"
fi
echo ""
echo "  服务状态: docker compose -f $COMPOSE_FILE ps"
echo "  查看日志: docker compose -f $COMPOSE_FILE logs -f"
echo "  重启服务: docker compose -f $COMPOSE_FILE restart"
echo "  停止服务: docker compose -f $COMPOSE_FILE down"
echo "  更新部署: git pull && docker compose -f $COMPOSE_FILE up -d --build"
echo ""
echo "  数据库备份: $BACKUP_DIR/"
echo ""

# 显示服务状态
docker compose -f $COMPOSE_FILE ps
