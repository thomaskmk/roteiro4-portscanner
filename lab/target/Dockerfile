FROM debian:bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
      python3 socat iptables iproute2 procps tini \
 && rm -rf /var/lib/apt/lists/*

COPY entrypoint.sh firewall.sh svc.sh latency.sh /usr/local/bin/
COPY www/ /srv/www/
RUN chmod +x /usr/local/bin/*.sh \
 && ln -s /usr/local/bin/svc.sh /usr/local/bin/svc \
 && ln -s /usr/local/bin/firewall.sh /usr/local/bin/firewall \
 && ln -s /usr/local/bin/latency.sh /usr/local/bin/latency

ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/entrypoint.sh"]
