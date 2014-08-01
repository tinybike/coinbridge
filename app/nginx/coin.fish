upstream backend {
    server 127.0.0.1:9090;
}

server {
    listen              80;
    server_name         coin.fish;

    gzip on;
    gzip_http_version 1.1;
    gzip_vary on;
    gzip_comp_level 6;
    gzip_proxied any;
    gzip_types text/plain text/css application/json application/x-javascript text/xml application/xml application/xml+rss text/javascript;
    gzip_buffers 16 8k;
    gzip_disable "MSIE [1-6].(?!.*SV1)";

    location / {
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header Host $http_host;
        proxy_set_header X-NginX-Proxy true;

        proxy_pass http://backend/;
        proxy_redirect off;

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection $connection_upgrade;

        access_log off;
        error_log /var/log/nginx/websockets.error.log;
    }

    location ~ ^/(robots.txt|favicon.ico)$ {
        root /home/deploy/deploy/coinbridge/app/static;
    }

    location /static {
        root   /home/deploy/deploy/coinbridge/app;
        expires max;
        add_header Cache-Control "public";
    }
}

server {
    listen  80;
    server_name www.coin.fish;
    rewrite ^/(.*) http://coin.fish/$1 permanent;
}
