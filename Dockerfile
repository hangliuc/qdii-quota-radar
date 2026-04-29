FROM python:3.11-slim

# 安装中文字体
RUN apt-get update && \
    apt-get install -y --no-install-recommends fonts-noto-cjk cron && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 数据和图片持久化目录
RUN mkdir -p /app/data /app/docs

# cron 定时任务：每天 8:40 北京时间执行
# 容器内设置为 Asia/Shanghai 时区
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 生成 crontab（环境变量通过 env 文件注入）
RUN echo '16 7 * * * cd /app && /usr/local/bin/python main.py >> /var/log/fund-monitor.log 2>&1' > /etc/cron.d/fund-monitor && \
    chmod 0644 /etc/cron.d/fund-monitor && \
    crontab /etc/cron.d/fund-monitor && \
    touch /var/log/fund-monitor.log

CMD ["sh", "-c", "printenv > /etc/environment && cron && tail -f /var/log/fund-monitor.log"]
