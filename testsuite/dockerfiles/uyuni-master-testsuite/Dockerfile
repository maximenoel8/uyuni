FROM registry.opensuse.org/systemsmanagement/uyuni/master/docker/containers/uyuni-master-testsuite
RUN zypper --non-interactive in avahi python3 python3-pip
RUN pip3 install --break-system-packages \
      "pytest>=7.4" \
      "pytest-bdd>=7.0" \
      "playwright>=1.40" \
      "paramiko>=3.4" \
      "httpx>=0.27" \
      "prometheus-client>=0.20" \
      "redis>=5.0" \
      "pytest-html>=4.0" && \
    playwright install chromium
